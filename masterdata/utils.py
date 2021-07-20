from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.contrib import messages
from cradle_of_mankind import settings
from csv import DictReader
import json
import os
import re
import random
from .models import (
    MasterData,
    MasterEntity,
    MasterValue,
    Source,
    SourceData,
    SourceEntity,
    SourceField,
    SourceValue,
    MasterField
)


def stage1_post(request, source, source_fields, stage):
    changed_source_fields = []
    for source_field in source_fields:
        if request.POST.get(source_field.name) == 'True':
            if not source_field.is_divided:
                source_field.is_divided = True
                changed_source_fields.append(source_field)
        else:
            if source_field.is_divided:
                source_field.is_divided = False
                source_field.delimiters = ''
                source_field.num_of_parts = 1
                changed_source_fields.append(source_field)
        source_field.save()
    source.masterdata_stage = stage
    if changed_source_fields:
        update_masterdata_rules(request, source, changed_source_fields)
    source.save()


def stage2_post(request, source, source_fields, stage):
    changed_source_fields = []
    for source_field in source_fields:
        original_delimiters = source_field.delimiters
        original_num_of_parts = source_field.num_of_parts
        source_field.delimiters = request.POST.get(
            source_field.name + '_delimiters')
        source_field.num_of_parts = int(request.POST.get(
            source_field.name + '_num_of_parts'))
        if source_field.delimiters != original_delimiters or source_field.num_of_parts != original_num_of_parts:
            changed_source_fields.append(source_field)
        source_field.save()
    source.masterdata_stage = stage
    if changed_source_fields:
        update_masterdata_rules(request, source, changed_source_fields)
    source.save()


def stage3_post(request, source, source_fields, masterdata_rules, stage):
    for source_field in source_fields:
        if source_field.is_divided:
            for i in range(1, source_field.num_of_parts+1):
                master_field_id = request.POST.get(
                    f"{source_field.id}_{i}_master")
                if master_field_id == '-1':
                    continue
                ordering = request.POST.get(
                    f"{source_field.id}_{i}_ordering")
                ending = request.POST.get(
                    f"{source_field.id}_{i}_ending")
                masterdata_rules[master_field_id][ordering] = {
                    'source_field': source_field.id,
                    'part': i,
                    'ending': ending}
        else:
            master_field_id = request.POST.get(
                f"{source_field.id}_master")
            if master_field_id == '-1':
                continue
            ordering = request.POST.get(f"{source_field.id}_ordering")
            ending = request.POST.get(f"{source_field.id}_ending")
            masterdata_rules[master_field_id][ordering] = {
                'source_field': source_field.id,
                'ending': ending}
    source.masterdata_rules = json.dumps(masterdata_rules)
    source.masterdata_stage = stage
    source.save()


def stage4_post(source, source_entity, master_entity, master_fields, master_rules):
    for master_field in master_fields:
        source_datas = []
        master_field_rules = master_rules[str(master_field.id)]
        if not master_field_rules:
            continue
        ordered_keys = sorted(list(master_field_rules.keys()))
        master_value = MasterValue()
        master_data = MasterData()
        master_value.master_field = master_field
        master_value.value = ''
        for key in ordered_keys:
            source_field = SourceField.objects.get(
                pk=master_field_rules[key]['source_field'])
            source_data = SourceData.objects.get(
                source_entity=source_entity, source_field=source_field)
            if source_field.is_divided:
                part = master_field_rules[key]['part']
                value = re.split(
                    source_field.delimiters, source_data.source_value.value)[part-1]
                master_value.value += value
                master_value.value += master_field_rules[key]['ending']
            else:
                master_value.value += source_data.source_value.value
                master_value.value += master_field_rules[key]['ending']
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


def get_selection_rules(source, master_fields):
    selection_rules = {}
    for source_field in source.sourcefield_set.all():
        if source_field.is_divided:
            selection_rules[source_field] = {}
            for part in range(1, source_field.num_of_parts+1):
                field_rules = {}
                selection_rules[source_field][part] = field_rules
                field_rules['master_field'] = None
                field_rules['ordering'] = 1
                field_rules['ending'] = ''
        else:
            field_rules = {}
            selection_rules[source_field] = {}
            selection_rules[source_field][1] = field_rules
            field_rules['master_field'] = None
            field_rules['ordering'] = 1
            field_rules['ending'] = ''
    if source.masterdata_rules:
        rules = json.loads(source.masterdata_rules)
        for master_field in master_fields.all():
            master_field_rules = rules[str(master_field.id)]
            for ordering in master_field_rules.keys():
                ending = master_field_rules[ordering]['ending']
                source_field = SourceField.objects.get(
                    pk=master_field_rules[ordering]['source_field'])
                if source_field.is_divided:
                    part = master_field_rules[ordering]['part']
                else:
                    part = 1
                selection_rules[source_field][part]['master_field'] = master_field
                selection_rules[source_field][part]['ordering'] = int(
                    ordering)
                selection_rules[source_field][part]['ending'] = ending
    return selection_rules


def update_masterdata_rules(request, source, source_fields):
    source_field_ids = list(map(lambda x: x.id, source_fields))
    if source.masterdata_rules:
        rules_changed = False
        rules = json.loads(source.masterdata_rules)
        for master_field_id in rules.keys():
            ordering_numbers = rules[master_field_id]
            for number in ordering_numbers:
                if ordering_numbers[number]['source_field'] in source_field_ids:
                    rules[master_field_id] = {}
                    rules_changed = True
                    break
        if rules_changed:
            source.masterdata_rules = json.dumps(rules)
            source.save()
            messages.info(request,
                          'You changed fields that had already been assigned some rules for mapping. Those were reseted in stage 3.')


def get_master_key_for_source_entity(source_entity, master_rules):
    master_key = ''
    primary_fields = MasterField.objects.filter(
        primary_key=True).order_by('pk')
    for master_field in primary_fields:
        master_field_rules = master_rules[str(master_field.id)]
        if not master_field_rules:
            continue
        ordered_keys = sorted(list(master_field_rules.keys()))
        for key in ordered_keys:
            source_field = SourceField.objects.get(
                pk=master_field_rules[key]['source_field'])
            source_data = SourceData.objects.get(
                source_entity=source_entity, source_field=source_field)
            if source_field.is_divided:
                part = master_field_rules[key]['part']
                value = re.split(
                    source_field.delimiters, source_data.source_value.value)[part-1]
                master_key += value
                master_key += master_field_rules[key]['ending']
            else:
                master_key += source_data.source_value.value
                master_key += master_field_rules[key]['ending']
    return master_key


def set_source_key_for_source_entity(source_entity):
    key_fields = source_entity.source.sourcefield_set.filter(
        is_primary_key=True)
    key_data = SourceData.objects.filter(
        source_entity=source_entity, source_field__is_primary_key=True)
    key_field_values = []
    for data in key_data:
        key_field_values.append(data.source_value.value)
    source_key = '-'.join(key_field_values)
    source_entity.source_key = source_key
    source_entity.save()


def create_examples(source):
    examples = {}
    for field in source.sourcefield_set.all():
        data = random.choice(field.sourcedata_set.all())
        if len(data.source_value.value) > 30:
            examples[field] = data.source_value.value[:30] + '...'
        else:
            examples[field] = data.source_value.value
    return examples


def create_examples_with_parts(source):
    examples = {}
    for field in source.sourcefield_set.all():
        data = random.choice(field.sourcedata_set.all())
        if field.is_divided:
            examples[field] = {}
            for i in range(1, field.num_of_parts+1):
                value = re.split(field.delimiters,
                                 data.source_value.value)[i-1]
                if len(value) > 30:
                    examples[field][i] = value[:30] + '...'
                else:
                    examples[field][i] = value
        else:
            if len(data.source_value.value) > 30:
                examples[field] = data.source_value.value[:30] + '...'
            else:
                examples[field] = data.source_value.value
    return examples


def create_example_table(source):
    rows = []
    source_entity_ids = list(
        source.sourceentity_set.all().values_list('id', flat=True))
    source_entity_ids = random.sample(source_entity_ids, 5)
    source_entities = source.sourceentity_set.filter(pk__in=source_entity_ids)
    for source_entity in source_entities:
        row = {}
        master_rules = json.loads(source.masterdata_rules)
        for master_field in MasterField.objects.all():
            master_field_rules = master_rules[str(master_field.id)]
            ordered_keys = sorted(list(master_field_rules.keys()))
            master_value = ''
            for key in ordered_keys:
                source_field = SourceField.objects.get(
                    pk=master_field_rules[key]['source_field'])
                source_data = SourceData.objects.get(
                    source_entity=source_entity, source_field=source_field)
                if source_field.is_divided:
                    part = master_field_rules[key]['part']
                    value = re.split(source_field.delimiters,
                                     source_data.source_value.value)[part-1]
                    master_value += value
                    master_value += master_field_rules[key]['ending']
                else:
                    master_value += source_data.source_value.value
                    master_value += master_field_rules[key]['ending']
            row[master_field] = master_value
        rows.append(row)
    return rows


def get_master_sources():
    return Source.objects.filter(master_created=True)


def get_source_entity_data(entities, fields):
    data = {}
    for entity in entities:
        entity_data = []
        for field in fields:
            value = SourceData.objects.filter(
                source_entity=entity, source_field=field).first().source_value.value
            entity_data.append(value)
        data[entity] = entity_data
    return data


def get_source_entity_data_for_master_entity(master_entity):
    data = {}
    for entity in master_entity.source_entities.all():
        entity_data = []
        for field in entity.source.sourcefield_set.all():
            value = SourceData.objects.filter(
                source_entity=entity, source_field=field).first().source_value.value
            entity_data.append(value)
        data[entity] = entity_data


def get_master_entity_data(entities, fields):
    data = {}
    for entity in entities:
        entity_data = []
        for field in fields:
            master_data = MasterData.objects.filter(
                master_entity=entity, master_field=field).first()
            entity_data.append(master_data)
        data[entity] = entity_data
    return data


def get_separated_master_entity_data(master_entity, master_fields, source_entities):
    data = {}
    for source_entity in source_entities:
        entity_data = []
        master_values = MasterValue.objects.filter(
            source_data__source_entity=source_entity).distinct()
        for field in master_fields:
            master_value = master_values.get(master_field=field)
            entity_data.append(master_value)
        data[source_entity] = entity_data

    return data


def get_source(request):
    source_id = request.GET.get('source')
    if source_id:
        try:
            source = Source.objects.get(pk=source_id)
        except Source.DoesNotExist:
            source = Source.objects.all().first()
    else:
        source = Source.objects.all().first()
    return source


def get_source_entities(request, source):
    source_entities = SourceEntity.objects.filter(source=source)
    page = request.GET.get('page', 1)
    paginator = Paginator(source_entities, 15)
    try:
        page_entities = paginator.page(page)
    except PageNotAnInteger:
        page_entities = paginator.page(1)
    except EmptyPage:
        page_entities = paginator.page(paginator.num_pages)
    return page_entities


def get_all_master_entities(request):
    master_entities = MasterEntity.objects.all()
    page = request.GET.get('page', 1)
    paginator = Paginator(master_entities, 15)
    try:
        page_entities = paginator.page(page)
    except PageNotAnInteger:
        page_entities = paginator.page(1)
    except EmptyPage:
        page_entities = paginator.page(paginator.num_pages)
    return page_entities


def get_master_entities(request, search, matching, case_sensitive):
    if case_sensitive == 'yes':
        if matching == 'exact':
            master_entities = MasterEntity.objects.filter(
                masterdata__mastervalue__value__exact=search).distinct()
        elif matching == 'contains':
            master_entities = MasterEntity.objects.filter(
                masterdata__mastervalue__value__contains=search).distinct()
        elif matching == 'startswith':
            master_entities = MasterEntity.objects.filter(
                masterdata__mastervalue__value__startswith=search).distinct()
        elif matching == 'endswith':
            master_entities = MasterEntity.objects.filter(
                masterdata__mastervalue__value__endswith=search).distinct()
    elif case_sensitive == 'no':
        if matching == 'exact':
            master_entities = MasterEntity.objects.filter(
                masterdata__mastervalue__value__iexact=search).distinct()
        elif matching == 'contains':
            master_entities = MasterEntity.objects.filter(
                masterdata__mastervalue__value__icontains=search).distinct()
        elif matching == 'startswith':
            master_entities = MasterEntity.objects.filter(
                masterdata__mastervalue__value__istartswith=search).distinct()
        elif matching == 'endswith':
            master_entities = MasterEntity.objects.filter(
                masterdata__mastervalue__value__iendswith=search).distinct()
    page = request.GET.get('page', 1)
    paginator = Paginator(master_entities, 15)
    try:
        page_entities = paginator.page(page)
    except PageNotAnInteger:
        page_entities = paginator.page(1)
    except EmptyPage:
        page_entities = paginator.page(paginator.num_pages)
    return page_entities


def save_source_fields(source):
    file = source.source_file
    delimiter = source.delimiter
    with open(file.path, encoding='utf8') as f:
        data = DictReader(f, delimiter=delimiter)
        print("Processing source fields...")
        for ordering, fieldname in enumerate(data.fieldnames, 1):
            try:
                source_field = SourceField.objects.filter(
                    source=source).get(name=fieldname)
            except SourceField.DoesNotExist:
                source_field = SourceField()
                source_field.source = source
                source_field.name = fieldname
                source_field.display_order = ordering
                source_field.save()


def save_data(source):
    delimiter = source.delimiter
    with open(source.source_file.path, encoding='utf8') as f:
        data = DictReader(f)
        rows = 0
        for row in data:
            rows += 1
        f.seek(0)
        data = DictReader(f, delimiter=delimiter)
        print(f"Processing... ({rows} rows)")
        for index, row in enumerate(data, 1):
            print_progress(index, rows)

            source_entity = SourceEntity()
            source_entity.source = source
            source_entity.save()

            for field in row.keys():
                source_field = SourceField.objects.filter(
                    source=source).get(name=field)

                source_data = SourceData()
                source_data.source_entity = source_entity
                source_data.source_field = source_field
                source_data.save()

                source_value = SourceValue()
                source_value.value = row[field]
                source_value.source_field = source_field
                source_value.source_data = source_data
                source_value.save()

            set_source_key_for_source_entity(source_entity)


def print_progress(index, rows):
    div = rows//5
    if index % div == 0 and div != 0:
        print(f"Processing... ({(2*index)//div}0% done)")


def save_uploaded_file(f):
    try:
        os.mkdir(os.path.join(settings.MEDIA_ROOT, 'masterdata'))
    except:
        pass

    path_to_file = os.path.join(settings.MEDIA_ROOT, 'masterdata', f.name)
    with open(path_to_file, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def set_primary_keys(request, source_fields):
    for source_field in source_fields:
        if request.POST[source_field.name] == 'True':
            source_field.is_primary_key = True
            source_field.save()
