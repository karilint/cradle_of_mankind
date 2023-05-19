from masterdata.templatetags.my_filters import to_string
from django.db import transaction
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.contrib import messages
from cradle_of_mankind import settings
from csv import DictReader
import json
import os
import re
import random
from .models import (
    Source,
    SourceEntity,
    SourceField,
    SourceData,
    MasterEntity,
    MasterField,
    MasterData,
    Value,
)

import logging

logger = logging.getLogger(__name__)

from django.db import connection, reset_queries


def get_user_access_level(request):
    if request.user.is_authenticated:
        if request.user.is_data_admin:
            return 4
        elif request.user.is_editor:
            return 3
        return 2
    return 1


def stage1_post(request, source, source_fields, stage):
    changed_source_fields = []
    for source_field in source_fields:
        source_field_changed = False
        if request.POST.get(source_field.name) == "True":
            if not source_field.is_divided:
                source_field.is_divided = True
                source_field_changed = True
        else:
            if source_field.is_divided:
                source_field.is_divided = False
                source_field.delimiters = ""
                source_field.num_of_parts = 1
                source_field_changed = True
        prev_num_of_mappings = source_field.num_of_mappings
        source_field.num_of_mappings = request.POST.get(
            source_field.name + "_num_of_mappings"
        )
        if prev_num_of_mappings != source_field.num_of_mappings:
            source_field_changed = True
        if source_field_changed:
            changed_source_fields.append(source_field)
    if changed_source_fields:
        SourceField.objects.bulk_update(
            changed_source_fields,
            ["is_divided", "delimiters", "num_of_parts", "num_of_mappings"],
        )
        update_masterdata_rules(request, source, changed_source_fields)
    source.masterdata_stage = stage
    source.save()


def stage2_post(request, source, source_fields, stage):
    changed_source_fields = []
    for source_field in source_fields:
        original_delimiters = source_field.delimiters
        original_num_of_parts = source_field.num_of_parts
        source_field.delimiters = request.POST.get(
            source_field.name + "_delimiters"
        )
        source_field.num_of_parts = int(
            request.POST.get(source_field.name + "_num_of_parts")
        )
        if (
            source_field.delimiters != original_delimiters
            or source_field.num_of_parts != original_num_of_parts
        ):
            changed_source_fields.append(source_field)
        source_field.save()
    source.masterdata_stage = stage
    if changed_source_fields:
        update_masterdata_rules(request, source, changed_source_fields)
    source.save()


def stage3_post(request, source, source_fields, masterdata_rules, stage):
    for source_field in source_fields:
        for num in range(1, source_field.num_of_mappings + 1):
            if source_field.is_divided:
                for i in range(1, source_field.num_of_parts + 1):
                    master_field_id = request.POST.get(
                        f"{source_field.id}_{i}_master_{num}"
                    )
                    if master_field_id == "-1":
                        continue
                    ordering = request.POST.get(
                        f"{source_field.id}_{i}_ordering_{num}"
                    )
                    ending = request.POST.get(
                        f"{source_field.id}_{i}_ending_{num}"
                    )
                    masterdata_rules.setdefault(master_field_id, {})
                    masterdata_rules[master_field_id][ordering] = {
                        "source_field": source_field.id,
                        "part": i,
                        "ending": ending,
                    }
            else:
                master_field_id = request.POST.get(
                    f"{source_field.id}_master_{num}"
                )
                if master_field_id == "-1":
                    continue
                ordering = request.POST.get(
                    f"{source_field.id}_ordering_{num}"
                )
                ending = request.POST.get(f"{source_field.id}_ending_{num}")
                masterdata_rules.setdefault(master_field_id, {})
                masterdata_rules[master_field_id][ordering] = {
                    "source_field": source_field.id,
                    "ending": ending,
                }
    source.masterdata_rules = json.dumps(masterdata_rules)
    source.masterdata_stage = stage
    source.save()


def stage4_post(
    source, source_entity, master_entity, master_fields, master_rules
):
    for master_field in master_fields:
        source_datas = []
        master_field_rules = master_rules.get(str(master_field.id), None)
        if not master_field_rules:
            continue
        ordered_keys = sorted(list(master_field_rules.keys()))
        master_value = MasterValue()
        master_data = MasterData()
        master_value.master_field = master_field
        master_value.value = ""
        for key in ordered_keys:
            source_field = SourceField.objects.get(
                pk=master_field_rules[key]["source_field"]
            )
            source_data = SourceData.objects.get(
                source_entity=source_entity, source_field=source_field
            )
            if source_field.is_divided:
                part = master_field_rules[key]["part"]
                try:
                    value = re.split(
                        source_field.delimiters, source_data.source_value.value
                    )[part - 1]
                except IndexError:
                    logger.warning(
                        f'Splitting not possible. Tried to get part {part} of "{source_data.source_value.value}". Using Empty string.'
                    )
                    value = ""
                master_value.value += value
                master_value.value += master_field_rules[key]["ending"]
            else:
                master_value.value += source_data.source_value.value
                master_value.value += master_field_rules[key]["ending"]
            source_datas.append(source_data)
        master_data.master_entity = master_entity
        master_data.master_field = master_field
        master_data.save()
        master_value.master_data = master_data
        master_value.save()
        for data in source_datas:
            master_data.source_data.add(data)
            master_value.source_data.add(data)
        master_field.save()


def get_master_value(
    source,
    source_entity,
    master_field,
    source_field_dict=None,
    source_data_dict=None,
):
    master_rules = json.loads(source.masterdata_rules)
    master_field_rules = master_rules.get(str(master_field.id), None)
    if not master_field_rules:
        return ""
    ordered_keys = sorted(list(master_field_rules.keys()))
    master_value = ""
    for key in ordered_keys:
        if source_field_dict:
            source_field = source_field_dict[
                master_field_rules[key]["source_field"]
            ]
        else:
            source_field = SourceField.objects.get(
                pk=master_field_rules[key]["source_field"]
            )
        if source_data_dict:
            source_data = source_data_dict[source_entity.id][source_field.id]
        else:
            source_data = SourceData.objects.select_related("value").get(
                source_entity=source_entity, source_field=source_field
            )
        if source_field.is_divided:
            part = master_field_rules[key]["part"]
            try:
                value = re.split(
                    source_field.delimiters, source_data.value.value
                )[part - 1]
            except IndexError:
                logger.warning(
                    f'Splitting not possible. Tried to get part {part} of "{source_data.value.value}". Using Empty string.'
                )
                value = ""
            master_value += value
            master_value += master_field_rules[key]["ending"]
        else:
            master_value += source_data.value.value
            master_value += master_field_rules[key]["ending"]
    return master_value.strip()


def get_master_source_data_ids(
    source,
    source_entity,
    master_field,
    source_field_dict=None,
    source_data_dict=None,
):
    source_data_ids = set()
    master_rules = json.loads(source.masterdata_rules)
    master_field_rules = master_rules.get(str(master_field.id), None)
    if not master_field_rules:
        return {}
    ordered_keys = sorted(list(master_field_rules.keys()))
    for key in ordered_keys:
        if source_field_dict:
            source_field = source_field_dict[
                master_field_rules[key]["source_field"]
            ]
        else:
            source_field = SourceField.objects.get(
                pk=master_field_rules[key]["source_field"]
            )
        if source_data_dict:
            source_data = source_data_dict[source_entity.id][source_field.id]
        else:
            source_data = SourceData.objects.select_related("value").get(
                source_entity=source_entity, source_field=source_field
            )
        source_data_ids.add(source_data.id)
    return source_data_ids


def get_selection_rules(source, master_fields):
    selection_rules = {}
    for source_field in source.source_fields.all():
        if source_field.is_divided:
            selection_rules[source_field] = {}
            for part in range(1, source_field.num_of_parts + 1):
                field_rules = {}
                selection_rules[source_field][part] = field_rules
                field_rules["master_field"] = None
                field_rules["ordering"] = 1
                field_rules["ending"] = ""
        else:
            field_rules = {}
            selection_rules[source_field] = {}
            selection_rules[source_field][1] = field_rules
            field_rules["master_field"] = None
            field_rules["ordering"] = 1
            field_rules["ending"] = ""
    if source.masterdata_rules:
        rules = json.loads(source.masterdata_rules)
        for master_field in master_fields.all():
            master_field_rules = rules.get(str(master_field.id), None)
            if not master_field_rules:
                continue
            for ordering in master_field_rules.keys():
                ending = master_field_rules[ordering]["ending"]
                source_field = SourceField.objects.get(
                    pk=master_field_rules[ordering]["source_field"]
                )
                if source_field.is_divided:
                    part = master_field_rules[ordering]["part"]
                else:
                    part = 1
                selection_rules[source_field][part][
                    "master_field"
                ] = master_field
                selection_rules[source_field][part]["ordering"] = int(ordering)
                selection_rules[source_field][part]["ending"] = ending
    return selection_rules


def update_masterdata_rules(request, source, source_fields):
    source_field_ids = list(map(lambda x: x.id, source_fields))
    if source.masterdata_rules:
        rules_changed = False
        rules = json.loads(source.masterdata_rules)
        for master_field_id in rules.keys():
            ordering_numbers = rules[master_field_id]
            for number in ordering_numbers:
                if (
                    ordering_numbers[number]["source_field"]
                    in source_field_ids
                ):
                    rules[master_field_id] = {}
                    rules_changed = True
                    break
        if rules_changed:
            source.masterdata_rules = json.dumps(rules)
            source.save()
            messages.info(
                request,
                (
                    "You changed fields that had already been assigned some rules"
                    "for mapping. Those were reseted in stage 3."
                ),
            )


def get_master_key_for_source_entity(source_entity, master_rules):
    master_key = ""
    primary_fields = MasterField.objects.filter(primary_key=True).order_by(
        "pk"
    )
    for master_field in primary_fields:
        master_field_rules = master_rules.get(str(master_field.id), None)
        if not master_field_rules:
            continue
        ordered_keys = sorted(list(master_field_rules.keys()))
        for key in ordered_keys:
            source_field = SourceField.objects.get(
                pk=master_field_rules[key]["source_field"]
            )
            source_data = SourceData.objects.select_related("value").get(
                source_entity=source_entity, source_field=source_field
            )
            if source_field.is_divided:
                part = master_field_rules[key]["part"]
                try:
                    value = re.split(
                        source_field.delimiters, source_data.value.value
                    )[part - 1]
                except IndexError:
                    logger.warning(
                        f'Splitting not possible. Tried to get part {part} of "{source_data.value.value}". Using Empty string.'
                    )
                    value = ""
                master_key += value
                master_key += master_field_rules[key]["ending"]
                continue
            master_key += source_data.value.value
            master_key += master_field_rules[key]["ending"]
    return master_key.strip()


def get_hidden_key(master_entity):
    other_hidden_keys = MasterEntity.objects.filter(
        master_key=master_entity.master_key
    ).values_list("hidden_key", flat=True)
    i = 0
    while i in other_hidden_keys:
        i += 1
    return i


def set_source_key_for_source_entity(source_entity):
    key_fields = source_entity.source.source_fields.filter(is_primary_key=True)
    key_data = SourceData.objects.filter(
        source_entity=source_entity, source_field__is_primary_key=True
    )
    key_field_values = []
    for data in key_data:
        key_field_values.append(data.source_value.value)
    source_key = "-".join(key_field_values)
    source_entity.source_key = source_key
    source_entity.save()


def get_source_key(source_fields, row):
    """Gets source_key for source_entity from csv row"""
    key_field_values = []
    for field in source_fields:
        if field.is_primary_key:
            key_field_values.append(row[field.name])
    return "-".join(key_field_values)


def create_examples(source):
    examples = {}
    source_entity = random.choice(source.source_entities.all())
    entity_values = Value.objects.filter(
        source_datas__source_entity=source_entity
    ).values_list("source_datas__source_field", "value")
    for field_id, value in entity_values:
        if len(value) > 30:
            examples[field_id] = value[:30] + "..."
        else:
            examples[field_id] = value
    return examples


def create_examples_with_parts(source):
    examples = {}
    source_entity = random.choice(source.source_entities.all())
    entity_values = Value.objects.filter(
        source_datas__source_entity=source_entity
    ).values_list(
        "source_datas__source_field__id",
        "source_datas__source_field__is_divided",
        "source_datas__source_field__delimiters",
        "source_datas__source_field__num_of_parts",
        "value",
    )
    for field_id, is_divided, delimiters, num_of_parts, value in entity_values:
        if is_divided:
            examples[field_id] = {}
            for i in range(1, num_of_parts + 1):
                try:
                    val = re.split(delimiters, value)[i - 1]
                except IndexError:
                    logger.warning(
                        f'Splitting not possible. Tried to get part {i} of "{value}". Using Empty string.'
                    )
                    val = ""
                if len(val) > 30:
                    examples[field_id][i] = val[:30] + "..."
                else:
                    examples[field_id][i] = val
        else:
            if len(value) > 30:
                examples[field_id] = value[:30] + "..."
            else:
                examples[field_id] = value
    return examples


def create_example_table(source):
    rows = []
    source_entity_ids = list(
        source.source_entities.all().values_list("id", flat=True)
    )
    source_entity_ids = random.sample(
        source_entity_ids, min(10, len(source_entity_ids))
    )
    source_entities = source.source_entities.filter(pk__in=source_entity_ids)
    source_fields = SourceField.objects.filter(source=source)
    master_fields = MasterField.objects.all()
    source_datas = SourceData.objects.select_related("value").filter(
        source_entity_id__in=source_entity_ids
    )
    source_data_dict = get_queryset_dict(source_datas, "source_entity_id")
    for k, v in source_data_dict.items():
        if isinstance(v, list):
            source_data_dict[k] = {obj.source_field_id: obj for obj in v}
            continue
        source_data_dict[k] = {v.source_field_id: v}
    source_field_dict = get_queryset_dict(source_fields)
    for source_entity in source_entities:
        row = {}
        for master_field in master_fields:
            master_value = get_master_value(
                source,
                source_entity,
                master_field,
                source_field_dict,
                source_data_dict,
            )
            row[master_field] = master_value
        rows.append(row)
    return rows


def get_master_sources():
    return Source.objects.filter(master_created=True)


def get_source_entity_data(entities, fields):
    """Returns a dictionary containing lists of values for each entity.
    Dictionary keys are entity ids. Dictionary values are lists of entity's data values.
    """
    data = {}
    raw_data = (
        Value.objects.filter(source_datas__source_entity__in=entities)
        .order_by("source_datas__source_field__id")
        .values_list("source_datas__source_entity", "value")
    )
    for entity_id, value in raw_data:
        data.setdefault(entity_id, [])
        data[entity_id].append(value)
    return data


def get_source_entity_data_for_master_entity(master_entity):
    data = {}
    for entity in master_entity.source_entities.all():
        entity_data = []
        for field in entity.source.source_fields.all():
            value = (
                SourceData.objects.filter(
                    source_entity=entity, source_field=field
                )
                .first()
                .source_value.value
            )
            entity_data.append(value)
        data[entity] = entity_data


def get_master_entity_data(master_entities, master_fields):
    data = {}
    master_datas = MasterData.objects.filter(master_entity__in=master_entities)
    master_data_dict = get_queryset_dict()
    for master_entity in master_entities:
        entity_data = []
        for master_field in master_fields:
            master_datas = (
                MasterData.objects.select_related("value")
                .filter(master_entity=entity, master_field=field)
                .first()
            )
            entity_data.append(master_data)
        data[entity] = entity_data
    return data


def get_separated_master_entity_data(
    master_entity, master_fields, source_entities
):
    data = {}
    for source_entity in source_entities:
        entity_data = []
        values = Value.objects.filter(
            source_data__source_entity=source_entity
        ).distinct()
        master_datas = MasterData.objects.filter(
            source_datas__source_entity=source_entity
        ).distinct()
        for field in master_fields:
            master_value = master_values.get(master_field=field)
            entity_data.append(master_value)
        data[source_entity] = entity_data

    return data


def get_source(request):
    source_id = request.GET.get("source")
    if source_id:
        try:
            source = Source.objects.get(pk=source_id)
        except Source.DoesNotExist:
            source = Source.objects.all().first()
    else:
        source = Source.objects.all().first()
    return source


def get_source_entities(request, source, size=15):
    source_entities = SourceEntity.objects.filter(source=source).order_by("id")
    page = request.GET.get("page", 1)
    paginator = Paginator(source_entities, size)
    try:
        page_entities = paginator.page(page)
    except PageNotAnInteger:
        page_entities = paginator.page(1)
    except EmptyPage:
        page_entities = paginator.page(paginator.num_pages)
    return page_entities


def get_master_entities_page(
    request, search, matching, case_sensitive, size=15
):
    master_entities = get_master_entities(search, matching, case_sensitive)
    page = request.GET.get("page", 1)
    paginator = Paginator(master_entities, size)
    try:
        page_entities = paginator.page(page)
    except PageNotAnInteger:
        page_entities = paginator.page(1)
    except EmptyPage:
        page_entities = paginator.page(paginator.num_pages)
    return page_entities


def get_master_entities(search, matching, case_sensitive):
    if not search:
        return MasterEntity.objects.all()
    if case_sensitive == "yes":
        if matching == "exact":
            master_entities = MasterEntity.objects.filter(
                master_datas__value__value__exact=search
            ).distinct()
        elif matching == "contains":
            master_entities = MasterEntity.objects.filter(
                master_datas__value__value__contains=search
            ).distinct()
        elif matching == "startswith":
            master_entities = MasterEntity.objects.filter(
                master_datas__value__value__startswith=search
            ).distinct()
        elif matching == "endswith":
            master_entities = MasterEntity.objects.filter(
                master_datas__value__value__endswith=search
            ).distinct()
    elif case_sensitive == "no":
        if matching == "exact":
            master_entities = MasterEntity.objects.filter(
                master_datas__value__value__iexact=search
            ).distinct()
        elif matching == "contains":
            master_entities = MasterEntity.objects.filter(
                master_datas__value__value__icontains=search
            ).distinct()
        elif matching == "startswith":
            master_entities = MasterEntity.objects.filter(
                master_datas__value__value__istartswith=search
            ).distinct()
        elif matching == "endswith":
            master_entities = MasterEntity.objects.filter(
                master_datas__value__value__iendswith=search
            ).distinct()
    return master_entities


def save_source_fields(source):
    file = source.source_file
    delimiter = source.delimiter
    with open(file.path, encoding="utf8") as f:
        data = DictReader(f, delimiter=delimiter)
        print("Processing source fields...")
        for ordering, fieldname in enumerate(data.fieldnames, 1):
            try:
                source_field = SourceField.objects.filter(source=source).get(
                    name=fieldname
                )
            except SourceField.DoesNotExist:
                source_field = SourceField()
                source_field.source = source
                source_field.name = fieldname
                source_field.display_order = ordering
                source_field.save()


def create_source_fields(source):
    """Creates a list of source fields for source based on the source file.
    Returns the list."""

    source_fields = []
    file = source.source_file
    delimiter = source.delimiter
    with open(file.path, encoding="utf8") as f:
        data = DictReader(f, delimiter=delimiter)
        print("Processing source fields...")
        for ordering, fieldname in enumerate(data.fieldnames, 1):
            source_field = SourceField()
            source_field.source = source
            source_field.name = fieldname
            source_field.display_order = ordering
            source_fields.append(source_field)
    return source_fields


def get_source_fields(source):
    """Returns a list of the names of the source's source fields."""

    source_fields = []
    file = source.source_file
    delimiter = source.delimiter
    with open(file.path, encoding="utf8") as f:
        data = DictReader(f, delimiter=delimiter)
        print("Processing source fields...")
        for fieldname in data.fieldnames:
            source_fields.append(fieldname)
    return source_fields


def get_queryset_dict(queryset, key_field="pk", inner_dict_key=None):
    """Returns a dictionary of given queryset's objects.

    Keyword arguments:
    queryset -- queryset whose objects used as dict values
    key_field -- the field(s) used as a dict key (default 'pk')
    inner_dict_key -- key used to create inner dictionary (default None)
    """
    dictionary = {}
    for obj in queryset:
        key_value = getattr(obj, key_field)
        if key_value in dictionary:
            dict_value = dictionary[key_value]
            if isinstance(dict_value, list):
                dictionary[key_value].append(obj)
                continue
            dict_value = [dict_value, obj]
            dictionary[key_value] = dict_value
            continue
        dictionary[key_value] = obj
    if inner_dict_key:
        for k, v in dictionary.items():
            if isinstance(v, list):
                dictionary[k] = get_queryset_dict(v, inner_dict_key)
                continue
            dictionary[k] = {getattr(v, inner_dict_key): v}
    return dictionary


def get_rows(search, matching, case_sensitive):
    rows = []
    master_fields = MasterField.objects.exclude(display_order=None)
    master_entities = get_master_entities(search, matching, case_sensitive)
    master_datas = MasterData.objects.select_related("value").filter(
        master_entity__in=master_entities
    )
    master_data_dict = get_queryset_dict(
        master_datas, "master_entity_id", "master_field_id"
    )
    rows.append(master_fields.values_list("name", flat=True))
    for master_entity in master_entities:
        row = []
        for master_field in master_fields:
            master_data = master_data_dict[master_entity.id].get(
                master_field.id
            )
            row.append(to_string(master_data))
        rows.append(row)
    return rows


def print_progress(index, rows):
    div = rows // 5
    if index % div == 0 and div != 0:
        print(f"Processing... ({(2*index)//div}0% done)")


def save_uploaded_file(f):
    try:
        os.mkdir(os.path.join(settings.MEDIA_ROOT, "masterdata"))
    except:
        pass

    path_to_file = os.path.join(settings.MEDIA_ROOT, "masterdata", f.name)
    with open(path_to_file, "wb+") as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def set_primary_keys(request_post, source_fields):
    for source_field in source_fields:
        if request_post[source_field.name] == "True":
            source_field.is_primary_key = True


def fix_non_trimmed_values():
    master_values = Value.objects.all()
    for mv in master_values:
        if mv.value == mv.value.strip():
            continue
        print(f"Updating value id {mv.id}")
        trimmed_value = mv.value.strip()
        new_value = None
        for value in Value.objects.filter(value=trimmed_value).all():
            if value.value == value.value.strip():
                new_value = value
        if new_value is None:
            new_value = Value.objects.create(value=trimmed_value)
        related_masterdatas = mv.master_datas.all()
        for md in related_masterdatas:
            md.value = new_value
        MasterData.objects.bulk_update(related_masterdatas, ["value"])
    Value.objects.filter(master_datas__isnull=True).filter(
        source_datas__isnull=True
    ).delete()
