from django.core.exceptions import ObjectDoesNotExist
from cradle_of_mankind.decorators import remember_last_query_params
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from cradle_of_mankind import settings
from csv import DictReader
import json
import os
import re
import random
from django.contrib import messages
from masterdata.forms import MasterFieldForm, SourceDataImportForm
from users.views import user_is_data_admin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from masterdata.models import (
    EditComment, MasterData, MasterEntity, MasterValue, Source,
    SourceData,
    SourceEntity,
    SourceField,
    SourceValue,
    MasterField
)


@login_required
@user_passes_test(user_is_data_admin)
def master_field_edit_display_order(request):
    master_fields = MasterField.objects.exclude(name='Empty').order_by('name')
    if request.method == 'POST':
        for field in master_fields:
            new_value = request.POST[field.name]
            if new_value == '0':
                field.display_order = None
            else:
                field.display_order = int(new_value)
            field.save()
        return redirect('master-fields')
    options = list(range(1, len(master_fields) + 1))
    current_display_orders = {}
    for field in master_fields:
        current_display_orders[field.name] = field.display_order
    return render(request, 'masterdata/master_field_edit_display_order.html',
                  {'master_fields': master_fields,
                   'options': options,
                   'current_display_orders': current_display_orders})


@login_required
@user_passes_test(user_is_data_admin)
def master_data_edit(request, master_data_pk):
    data = MasterData.objects.get(pk=master_data_pk)
    if request.method == 'POST':
        new_value = request.POST['new_value']
        old_value = data.master_value
        try:
            master_value = MasterValue.objects.filter(
                master_field=data.master_field).get(value=new_value)
        except MasterValue.DoesNotExist:
            master_value = MasterValue()
            master_value.value = new_value
            master_value.master_field = data.master_field
            master_value.save()
        data.master_value = master_value
        data.save()
        comment = EditComment()
        comment.text = request.POST['comment']
        comment.prev_value = old_value.value
        comment.new_value = new_value
        comment.masterdata = data
        comment.save()
        if not old_value.masterdata_set.all():
            old_value.delete()
        return redirect('master-list')

    source = data.master_entity.source
    source_data = data.source_data.first()
    comments = data.editcomment_set.all()
    return render(request, 'masterdata/master_data_edit.html',
                  {'data': data,
                   'source': source,
                   'source_data': source_data,
                   'comments': comments})


@ login_required
@ user_passes_test(user_is_data_admin)
def master_field_delete(request, master_field_pk):
    master_field = MasterField.objects.get(pk=master_field_pk)
    if request.method == 'POST':
        if master_field.name == 'Empty':
            messages.error(request, "You cannot delete the Empty field!")
        elif len(master_field.sources.all()) == 0:
            master_field.delete()
            messages.success(
                request, "The master field was deleted succesfully!")
        else:
            messages.error(request,
                           "The master field could not be deleted. There are some sources that are using it!")
        return redirect('master-fields')
    return render(request, 'masterdata/master_field_delete.html',
                  {'master_field': master_field})


@login_required
@user_passes_test(user_is_data_admin)
def master_field_edit(request, master_field_pk):
    master_field = MasterField.objects.get(pk=master_field_pk)
    if request.method == 'POST':
        form = MasterFieldForm(request.POST, instance=master_field)
        if form.is_valid():
            form.save()
            messages.success(request, 'The master field has been updated!')
            return redirect('master-fields')
    else:
        form = MasterFieldForm(instance=master_field)
    return render(request, 'masterdata/master_field_edit.html',
                  {'form': form,
                   'master_field': master_field})


@login_required
@user_passes_test(user_is_data_admin)
def manage_masters(request):
    sources = Source.objects.all()
    return render(request, 'masterdata/manage_masters.html',
                  {'sources': sources})


@login_required
@user_passes_test(user_is_data_admin)
def edit_master(request, source_pk):
    source = Source.objects.get(pk=source_pk)
    if request.method == 'POST':
        pass
    source_fields = source.sourcefield_set.all()
    master_fields = MasterField.objects.all().order_by('name')
    examples = create_examples(source)
    return render(request, 'masterdata/edit_master.html',
                  {'source': source,
                   'source_fields': source_fields,
                   'master_fields': master_fields,
                   'examples': examples})


@login_required
@user_passes_test(user_is_data_admin)
def create_master(request, source_pk, stage):
    source = Source.objects.get(pk=source_pk)

    if stage == 1:
        source_fields = source.sourcefield_set.all()
        if request.method == 'POST':
            data_was_changed = False
            for source_field in source_fields:
                if request.POST.get(source_field.name) == 'True':
                    if not source_field.is_divided:
                        source_field.is_divided = True
                        data_was_changed = True
                else:
                    if source_field.is_divided:
                        source_field.is_divided = False
                        source_field.delimiters = ''
                        source_field.num_of_parts = 1
                        data_was_changed = True
                source_field.save()
            source.masterdata_stage = stage
            if data_was_changed:
                source.masterdata_rules = ''
            source.save()
            return redirect('create-master', source_pk, stage+1)
        examples = create_examples(source)
        return render(request, 'masterdata/create_master_stage1.html',
                      {'source': source,
                       'source_fields': source_fields,
                       'examples': examples})

    elif stage == 2:
        source_fields = source.sourcefield_set.filter(is_divided=True)
        if request.method == 'POST':
            data_was_changed = False
            for source_field in source_fields:
                original_delimiters = source_field.delimiters
                original_num_of_parts = source_field.num_of_parts
                source_field.delimiters = request.POST.get(
                    source_field.name + '_delimiters')
                source_field.num_of_parts = int(request.POST.get(
                    source_field.name + '_num_of_parts'))
                if source_field.delimiters != original_delimiters or source_field.num_of_parts != original_num_of_parts:
                    data_was_changed = True
                source_field.save()
            source.masterdata_stage = stage
            if data_was_changed:
                source.masterdata_rules = ''
            source.save()
            if "next" in request.POST:
                next_stage = stage+1
            else:
                next_stage = stage-1
            return redirect('create-master', source_pk, next_stage)
        examples = create_examples(source)
        return render(request, 'masterdata/create_master_stage2.html',
                      {'source': source,
                       'source_fields': source_fields,
                       'examples': examples})

    elif stage == 3:
        source_fields = source.sourcefield_set.all()
        master_fields = MasterField.objects.all()
        if request.method == 'POST':
            masterdata_rules = {}
            for master_field in master_fields:
                masterdata_rules[master_field.id] = {}
            for source_field in source_fields:
                if source_field.is_divided:
                    for i in range(1, source_field.num_of_parts+1):
                        master_field_id = int(request.POST.get(
                            f"{source_field.id}_{i}_master"))
                        ordering = request.POST.get(
                            f"{source_field.id}_{i}_ordering")
                        ending = request.POST.get(
                            f"{source_field.id}_{i}_ending")
                        masterdata_rules[master_field_id][ordering] = {
                            'source_field': source_field.id,
                            'part': i,
                            'ending': ending}
                else:
                    master_field_id = int(request.POST.get(
                        f"{source_field.id}_master"))
                    ordering = request.POST.get(f"{source_field.id}_ordering")
                    ending = request.POST.get(f"{source_field.id}_ending")
                    masterdata_rules[master_field_id][ordering] = {
                        'source_field': source_field.id,
                        'ending': ending}
            source.masterdata_rules = json.dumps(masterdata_rules)
            source.masterdata_stage = stage
            source.save()
            if "next" in request.POST:
                next_stage = stage+1
            else:
                next_stage = stage-1
            return redirect('create-master', source_pk, next_stage)
        selection_rules = {}
        for source_field in source_fields:
            if source_field.is_divided:
                selection_rules[source_field] = {}
                for part in range(1, source_field.num_of_parts+1):
                    field_rules = {}
                    selection_rules[source_field][part] = field_rules
                    field_rules['master_field'] = MasterField.objects.get(
                        name='Empty')
                    field_rules['ordering'] = 1
                    field_rules['ending'] = ''
            else:
                field_rules = {}
                selection_rules[source_field] = {}
                selection_rules[source_field][1] = field_rules
                field_rules['master_field'] = MasterField.objects.get(
                    name='Empty')
                field_rules['ordering'] = 1
                field_rules['ending'] = ''
        if source.masterdata_rules:
            rules = json.loads(source.masterdata_rules)
            for master_field in master_fields.exclude(name='Empty'):
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
        examples = create_examples_with_parts(source)
        return render(request, 'masterdata/create_master_stage3.html',
                      {'source': source,
                       'source_fields': source_fields,
                       'master_fields': master_fields,
                       'rules': selection_rules,
                       'examples': examples})

    elif stage == 4:
        if request.method == 'POST':
            for source_entity in source.sourceentity_set.all():
                master_entity = MasterEntity()
                master_entity.source = source
                master_entity.save()
                master_entity.source_entity.add(source_entity)
                master_rules = json.loads(source.masterdata_rules)

                for master_field in MasterField.objects.exclude(name='Empty'):
                    source_datas = []
                    master_field_rules = master_rules[str(master_field.id)]
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
                    master_value.save()
                    master_data.master_entity = master_entity
                    master_data.master_field = master_field
                    master_data.master_value = master_value
                    master_data.save()
                    for data in source_datas:
                        master_data.source_data.add(data)
                    master_field.sources.add(source)
                    master_field.save()
            source.master_created = True
            source.save()
            return redirect('manage-masters')
        source_fields = source.sourcefield_set.all()
        master_fields = MasterField.objects.exclude(name='Empty')
        example_table = create_example_table(source)
        return render(request, 'masterdata/create_master_stage4.html',
                      {'source': source,
                       'source_fields': source_fields,
                       'master_fields': master_fields,
                       'example_table': example_table})


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
        for master_field in MasterField.objects.exclude(name='Empty'):
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


@login_required
@user_passes_test(user_is_data_admin)
def master_fields(request):
    if request.method == 'POST':
        form = MasterFieldForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "The field was added succesfully.")
            return redirect('master-fields')
        else:
            messages.error(
                request, "Cannot add that field. Did you try to add a field that already exists?")
    master_fields = MasterField.objects.exclude(name='Empty').order_by('name')
    form = MasterFieldForm()
    return render(request, 'masterdata/master_fields.html',
                  {'master_fields': master_fields,
                   'form': form})


@login_required
@user_passes_test(user_is_data_admin)
@remember_last_query_params('master-list', ['page', 'source'])
def master_list(request):
    master_sources = get_master_sources()
    if len(master_sources) < 1:
        if len(Source.objects.all()) < 1:
            messages.error(
                request, "You haven't yet created any masterdata. Please import a source and then create a master from it.")
            return redirect('import-source-data')
        else:
            messages.error(
                request, "You haven't yet created any masterdata. Please pick an existing source and create masterdata from it.")
            return redirect('manage-masters')
    if request.GET.get('source') == 'all':
        master_fields = MasterField.objects.exclude(display_order=None)
        master_entities = get_all_master_entities(request)
        master_entity_data = get_master_entity_data(
            master_entities, master_fields)
    else:
        source = get_source(request)
        master_fields = source.masterfield_set.exclude(display_order=None)
        master_entities = get_master_entities(request, source)
        master_entity_data = get_master_entity_data(
            master_entities, master_fields)
    return render(request, 'masterdata/master_list.html',
                  {'selection_value': request.GET.get('source'),
                   'master_sources': master_sources,
                   'master_fields': master_fields,
                   'master_entity_data': master_entity_data,
                   'page_obj': master_entities})


@login_required
@user_passes_test(user_is_data_admin)
@remember_last_query_params('source-list', ['page', 'source'])
def source_list(request):
    sources = Source.objects.all()
    if len(sources) < 1:
        messages.error(
            request, "You haven't yet added any sources. Please import one first.")
        return redirect('import-source-data')
    source = get_source(request)
    source_fields = SourceField.objects.filter(source=source)
    source_entitites = get_source_entities(request, source)
    source_entity_data = get_source_entity_data(
        source_entitites, source_fields)
    return render(request, 'masterdata/source_list.html',
                  {'selected_source': source,
                   'sources': sources,
                   'source_fields': source_fields,
                   'source_entity_data': source_entity_data,
                   'page_obj': source_entitites})


def get_master_sources():
    master_sources = []
    for source in Source.objects.all():
        if len(source.masterentity_set.all()) != 0:
            master_sources.append(source)
    return master_sources


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


def get_master_entity_data(entities, fields):
    data = {}
    for entity in entities:
        entity_data = []
        for field in fields:
            value = MasterData.objects.filter(
                master_entity=entity, master_field=field).first()
            entity_data.append(value)
        data[entity] = entity_data
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


def get_master_entities(request, source):
    master_entities = MasterEntity.objects.filter(source=source)
    page = request.GET.get('page', 1)
    paginator = Paginator(master_entities, 15)
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


@login_required
@user_passes_test(user_is_data_admin)
def import_data(request):
    if request.method == 'POST':
        form = SourceDataImportForm(request.POST, request.FILES)
        if form.is_valid():
            source_name = request.POST['source_name']
            delimiter = request.POST['delimiter']
            f = request.FILES['file']
            save_uploaded_file(f)
            save_data(source_name, delimiter, f)
            verify_empty_field()
            messages.success(request, "Import was succesful!")
            redirect('index')
    form = SourceDataImportForm()
    return render(request, 'masterdata/import_source_data.html', {'form': form})


def verify_empty_field():
    try:
        MasterField.objects.get(name="Empty")
    except ObjectDoesNotExist:
        empty = MasterField()
        empty.name = "Empty"
        empty.description = ""
        empty.save()


def save_data(source_name, delimiter, file):
    with open(os.path.join(settings.MEDIA_ROOT, 'masterdata', file.name), encoding='utf8') as f:
        try:
            source = Source.objects.get(name=source_name)
        except Source.DoesNotExist:
            source = Source()
            source.name = source_name
            source.save()

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

            if index == 1:
                for order, key in enumerate(row.keys()):
                    try:
                        source_field = SourceField.objects.filter(
                            source=source).get(name=key)
                    except SourceField.DoesNotExist:
                        source_field = SourceField()
                    source_field.source = source
                    source_field.name = key
                    source_field.display_order = order
                    source_field.save()

            for field in row.keys():
                source_field = SourceField.objects.filter(
                    source=source).get(name=field)
                try:
                    source_value = SourceValue.objects.filter(
                        source_field=source_field).get(value=row[field])
                except SourceValue.DoesNotExist:
                    source_value = SourceValue()
                source_value.source_field = source_field
                source_value.value = row[field]
                source_value.save()

                try:
                    source_data = SourceData.objects.filter(source_entity=source_entity).filter(
                        source_field=source_field).get(source_value=source_value)
                except SourceData.DoesNotExist:
                    source_data = SourceData()
                source_data.source_entity = source_entity
                source_data.source_field = source_field
                source_data.source_value = source_value
                source_data.save()


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
