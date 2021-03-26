from django.core.exceptions import ObjectDoesNotExist
from cradle_of_mankind.decorators import remember_last_query_params
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from cradle_of_mankind import settings
from csv import DictReader
import os
from django.contrib import messages
from django.db import IntegrityError
from masterdata.forms import MasterFieldForm, SourceDataImportForm
from users.views import user_is_data_admin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from masterdata.models import (
    MasterData, MasterEntity, MasterValue, Source,
    SourceData,
    SourceEntity,
    SourceField,
    SourceValue,
    MasterField
)


@ login_required
@ user_passes_test(user_is_data_admin)
def edit_master(request):
    master_sources = []
    other_sources = []
    for source in Source.objects.all():
        if len(source.masterentity_set.all()) == 0:
            other_sources.append(source)
        else:
            master_sources.append(source)

    return render(request, 'masterdata/edit_master.html',
                  {'master_sources': master_sources,
                   'other_sources': other_sources})


@ login_required
@ user_passes_test(user_is_data_admin)
def create_master(request, source_pk):
    source = Source.objects.get(pk=source_pk)
    if request.method == 'POST':
        for source_entity in source.sourceentity_set.all():
            master_entity = MasterEntity()
            master_entity.source = source
            master_entity.save()
            master_entity.source_entity.add(source_entity)

            for source_data in source_entity.sourcedata_set.all():
                master_field_id = request.POST[source_data.source_field.name]
                master_field = MasterField.objects.get(pk=master_field_id)
                if master_field.name == 'Empty':
                    continue
                master_field.sources.add(source)
                master_field.save()

                master_value = MasterValue()
                master_value.master_field = master_field
                master_value.value = source_data.source_value.value
                master_value.save()

                master_data = MasterData()
                master_data.master_entity = master_entity
                master_data.master_field = master_field
                master_data.master_value = master_value
                master_data.save()
                master_data.source_data.add(source_data)
        return redirect('edit-master')

    source_fields = source.sourcefield_set.all()
    master_fields = MasterField.objects.all().order_by('name')
    return render(request, 'masterdata/create_master.html',
                  {'source': source,
                   'source_fields': source_fields,
                   'master_fields': master_fields})


@ login_required
@ user_passes_test(user_is_data_admin)
def master_fields(request):
    if request.method == 'POST':
        form = MasterFieldForm(request.POST)
        if form.is_valid():
            try:
                field_name = request.POST['field_name']
                field_description = request.POST['field_description']
                new_field = MasterField()
                new_field.name = field_name
                new_field.description = field_description
                new_field.save()
                messages.success(request, "The field was added succesfully.")
            except IntegrityError:
                messages.error(
                    request, "Cannot add that field. Did you try to add a field that already exists?")
            return redirect('master-fields')
    master_fields = MasterField.objects.all().order_by('name')
    form = MasterFieldForm()
    return render(request, 'masterdata/master_fields.html',
                  {'master_fields': master_fields,
                   'form': form})


@ login_required
@ user_passes_test(user_is_data_admin)
@ remember_last_query_params('master-list', ['page', 'source'])
def master_list(request):
    master_sources = get_master_sources()
    source = get_source(request)
    master_fields = source.masterfield_set.all()
    master_entities = get_master_entities(request, source)
    master_entity_data = get_master_entity_data(master_entities, master_fields)
    return render(request, 'masterdata/master_list.html',
                  {'selected_source': source,
                   'master_sources': master_sources,
                   'master_fields': master_fields,
                   'master_entity_data': master_entity_data,
                   'page_obj': master_entities})


@ login_required
@ user_passes_test(user_is_data_admin)
@ remember_last_query_params('source-list', ['page', 'source'])
def source_list(request):
    sources = Source.objects.all()
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
                master_entity=entity, master_field=field).first().master_value.value
            entity_data.append(value)
        data[entity] = entity_data
    return data


def get_source(request):
    source_id = request.GET.get('source')
    if source_id:
        source = Source.objects.get(pk=source_id)
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
        print(rows)
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
