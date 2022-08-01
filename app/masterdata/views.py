import json
import re
import csv
from cradle_of_mankind.settings import MEDIA_ROOT
from cradle_of_mankind.decorators import remember_last_query_params
from django.contrib import messages
from django.http import HttpResponse, StreamingHttpResponse
from users.views import user_is_data_admin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from .forms import MasterFieldForm, SourceDataImportForm
from .utils import *
from .models import (
    EditComment,
    MasterData,
    MasterEntity,
    MasterValue,
    Source,
    SourceData,
    SourceField,
    MasterField
)

import logging

logger = logging.getLogger(__name__)


@remember_last_query_params('master-list', ['page', 'search', 'matching', 'case-sensitive'])
def index(request):
    master_sources = get_master_sources()
    search = request.GET.get('search', default='').strip()
    matching = request.GET.get('matching', default='exact')
    case_sensitive = request.GET.get('case-sensitive', default='yes')
    master_fields = MasterField.objects.exclude(display_order=None)
    show_table = len(MasterEntity.objects.all()) > 0
    master_entities = get_master_entities_page(
        request, search, matching, case_sensitive)
    master_entity_data = get_master_entity_data(
        master_entities, master_fields)
    context = {
        'selection_value': request.GET.get('source'),
        'master_sources': master_sources,
        'master_fields': master_fields,
        'master_entity_data': master_entity_data,
        'page_obj': master_entities,
        'show_table': show_table,
    }
    if search:
        context['search'] = search
        context['matching'] = matching
        context['case_sensitive'] = case_sensitive
    else:
        context['search'] = ''
        context['matching'] = 'exact'
        context['case_sensitive'] = 'yes'

    return render(request, 'masterdata/masterdata-index.html', context)


@login_required
@user_passes_test(user_is_data_admin)
def manage_masters(request):
    sources = Source.objects.all()
    if len(sources) < 1:
        messages.info(
            request, "You haven't yet added any sources. Please import one first.")
        return redirect('import-source-data')
    return render(request, 'masterdata/manage_masters.html',
                  {'sources': sources})


@login_required
@user_passes_test(user_is_data_admin)
@transaction.atomic
def create_master(request, source_pk, stage):
    source = Source.objects.get(pk=source_pk)
    source_fields = source.sourcefield_set.all()
    title = "Create Master"

    if stage == 1:
        if request.method == 'POST':
            stage1_post(request, source, source_fields, stage)
            return redirect('create-master', source_pk, stage+1)
        examples = create_examples(source)
        instructions = 'Stage 1/4: Choose which fields need to be divided into parts and how many masters are they mapped to.'
        return render(request, 'masterdata/create_master_stage1.html',
                      {'title': title,
                       'instructions': instructions,
                       'source': source,
                       'source_fields': source_fields,
                       'examples': examples})

    elif stage == 2:
        source_fields = source_fields.filter(is_divided=True)
        if request.method == 'POST':
            stage2_post(request, source, source_fields, stage)
            next_stage = stage+1 if "next" in request.POST else stage-1
            return redirect('create-master', source_pk, next_stage)
        examples = create_examples(source)
        instructions = 'Stage 2/4: Give delimiters that will be used to divide the source fields you want to be in masterdata.'
        return render(request, 'masterdata/create_master_stage2.html',
                      {'title': title,
                       'instructions': instructions,
                       'source': source,
                       'source_fields': source_fields,
                       'examples': examples})

    elif stage == 3:
        master_fields = MasterField.objects.all()
        if request.method == 'POST':
            masterdata_rules = {}
            for master_field in master_fields:
                masterdata_rules[str(master_field.id)] = {}
            stage3_post(request, source, source_fields,
                        masterdata_rules, stage)
            next_stage = stage+1 if 'next' in request.POST else stage-1
            return redirect('create-master', source_pk, next_stage)
        selection_rules = get_selection_rules(
            source, master_fields)
        examples = create_examples_with_parts(source)
        instructions = 'Stage 3/4: Assign rules for master field mapping.'
        return render(request, 'masterdata/create_master_stage3.html',
                      {'title': title,
                       'instruction': instructions,
                       'source': source,
                       'source_fields': source_fields,
                       'master_fields': master_fields,
                       'rules': selection_rules,
                       'examples': examples})

    elif stage == 4:
        if request.method == 'POST':
            master_rules = json.loads(source.masterdata_rules)
            master_fields = MasterField.objects.all()
            for source_entity in source.sourceentity_set.all():
                master_key = get_master_key_for_source_entity(
                    source_entity, master_rules)
                try:
                    master_entity = MasterEntity.objects.get(
                        master_key=master_key)
                    master_entity.source_entities.add(source_entity)
                    for master_field in MasterField.objects.all():
                        source_datas = []
                        master_field_rules = master_rules[str(master_field.id)]
                        if not master_field_rules:
                            continue
                        ordered_keys = sorted(list(master_field_rules.keys()))
                        master_value = MasterValue()
                        master_data = MasterData.objects.get(
                            master_entity=master_entity, master_field=master_field)
                        master_value.master_field = master_field
                        master_value.value = ''
                        for key in ordered_keys:
                            source_field = SourceField.objects.get(
                                pk=master_field_rules[key]['source_field'])
                            source_data = SourceData.objects.get(
                                source_entity=source_entity, source_field=source_field)
                            if source_field.is_divided:
                                part = master_field_rules[key]['part']
                                try:
                                    value = re.split(
                                        source_field.delimiters, source_data.source_value.value)[part-1]
                                except IndexError:
                                    logger.warning(
                                        f'Splitting not possible. Tried to get part {part} of "{source_data.source_value.value}". Using Empty string.')
                                    value = ''
                                master_value.value += value
                                master_value.value += master_field_rules[key]['ending']
                            else:
                                master_value.value += source_data.source_value.value
                                master_value.value += master_field_rules[key]['ending']
                            source_datas.append(source_data)
                        master_value.master_data = master_data
                        master_value.save()
                        master_data.save()
                        for data in source_datas:
                            master_data.source_data.add(data)
                            master_value.source_data.add(data)
                        master_field.save()

                except MasterEntity.DoesNotExist:
                    master_entity = MasterEntity()
                    master_entity.master_key = master_key
                    master_entity.source = source
                    master_entity.save()
                    master_entity.source_entities.add(source_entity)
                    stage4_post(source, source_entity, master_entity,
                                master_fields, master_rules)
            source.master_created = True
            source.save()
            return redirect('manage-masters')
        master_fields = MasterField.objects.all()
        example_table = create_example_table(source)
        instructions = 'Stage 4/4: Sample rows with given rules. Looks good?'
        return render(request, 'masterdata/create_master_stage4.html',
                      {'title': title,
                       'instructions': instructions,
                       'source': source,
                       'master_fields': master_fields,
                       'example_table': example_table})


@login_required
@user_passes_test(user_is_data_admin)
def edit_master(request, source_pk, stage):
    source = Source.objects.get(pk=source_pk)
    source_field_ids = []
    for source_field in source.sourcefield_set.all():
        if len(source_field.sourcedata_set.first().masterdata_set.all()) == 0:
            source_field_ids.append(source_field.id)
    source_fields = SourceField.objects.filter(pk__in=source_field_ids)
    title = "Edit Master"

    if stage == 1:
        if request.method == 'POST':
            stage1_post(request, source, source_fields, stage)
            return redirect('edit-master', source_pk, stage+1)
        examples = create_examples(source)
        instructions = "Stage 1/4: Choose which fields need to be divided into parts "\
                       "(only the fields that haven't been mapped yet are shown)."
        return render(request, 'masterdata/create_master_stage1.html',
                      {'title': title,
                       'instructions': instructions,
                       'source': source,
                       'source_fields': source_fields,
                       'examples': examples})

    elif stage == 2:
        source_fields = source_fields.filter(is_divided=True)
        if request.method == 'POST':
            stage2_post(request, source, source_fields, stage)
            next_stage = stage+1 if "next" in request.POST else stage-1
            return redirect('edit-master', source_pk, next_stage)
        examples = create_examples(source)
        instructions = 'Stage 2/4: Give delimiters that will be used to divide the source fields you want to be in masterdata.'
        return render(request, 'masterdata/create_master_stage2.html',
                      {'title': title,
                       'instructions': instructions,
                       'source': source,
                       'source_fields': source_fields,
                       'examples': examples})

    elif stage == 3:
        master_fields = MasterField.objects.exclude(sources=source)
        if request.method == 'POST':
            if source.masterdata_rules:
                masterdata_rules = json.loads(source.masterdata_rules)
            else:
                masterdata_rules = {}
                for master_field in MasterField.objects.all():
                    masterdata_rules[master_field.id] = {}
            stage3_post(request, source, source_fields,
                        masterdata_rules, stage)
            next_stage = stage+1 if 'next' in request.POST else stage-1
            return redirect('edit-master', source_pk, next_stage)
        selection_rules = get_selection_rules(
            source, master_fields)
        examples = create_examples_with_parts(source)
        instructions = 'Stage 3/4: Assign rules for master field mapping.'
        return render(request, 'masterdata/create_master_stage3.html',
                      {'title': title,
                       'instruction': instructions,
                       'source': source,
                       'source_fields': source_fields,
                       'master_fields': master_fields,
                       'rules': selection_rules,
                       'examples': examples})

    elif stage == 4:
        if request.method == 'POST':
            master_rules = json.loads(source.masterdata_rules)
            master_fields = MasterField.objects.exclude(sources=source)
            for source_entity in source.sourceentity_set.all():
                master_entity = MasterEntity.objects.get(
                    source_entity=source_entity)
            stage4_post(source, source_entity, master_entity,
                        master_fields, master_rules)
            source.master_created = True
            source.save()
            return redirect('manage-masters')
        master_fields = MasterField.objects.all()
        example_table = create_example_table(source)
        instructions = 'Stage 4/4: Sample rows with given rules. Looks good?'
        return render(request, 'masterdata/create_master_stage4.html',
                      {'title': title,
                       'instructions': instructions,
                       'source': source,
                       'master_fields': master_fields,
                       'example_table': example_table})


@login_required
@user_passes_test(user_is_data_admin)
def delete_master(request, source_pk):
    source = Source.objects.get(pk=source_pk)
    if request.method == 'POST':
        MasterValue.objects.filter(
            source_data__source_entity__source=source).delete()
        MasterData.objects.filter(mastervalue__isnull=True).delete()
        MasterEntity.objects.filter(
            masterdata__isnull=True).delete()

        source_entities = SourceEntity.objects.filter(source=source)
        for source_entity in source_entities:
            source_entity.masterentity_set.clear()
        source_data = SourceData.objects.filter(source_entity__source=source)
        for data in source_data:
            data.masterdata_set.clear()

        source.master_created = False
        source.masterdata_stage = 0
        source.masterdata_rules = None
        source.save()
        messages.success(
            request, f"Master data for {source.name} has been deleted.")
        return redirect('manage-masters')
    return render(request, 'masterdata/delete_master.html',
                  {'source': source})


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
    master_fields = MasterField.objects.all()
    form = MasterFieldForm()
    return render(request, 'masterdata/master_fields.html',
                  {'master_fields': master_fields,
                   'form': form})


@login_required
@user_passes_test(user_is_data_admin)
def master_field_edit(request, master_field_pk):
    master_field = MasterField.objects.get(pk=master_field_pk)
    if request.method == 'POST':
        form = MasterFieldForm(request.POST, instance=master_field, initial={
                               'name': master_field.name,
                               'description': master_field.description,
                               'primary_key': master_field.primary_key})

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
def master_field_delete(request, master_field_pk):
    master_field = MasterField.objects.get(pk=master_field_pk)
    if request.method == 'POST':
        if len(master_field.masterdata_set.all()) == 0 and len(master_field.mastervalue_set.all()) == 0:
            master_field.delete()
            messages.success(
                request, "The master field was deleted succesfully!")
        else:
            messages.error(request,
                           "The master field could not be deleted. There is some master data using it!")
        return redirect('master-fields')
    return render(request, 'masterdata/master_field_delete.html',
                  {'master_field': master_field})


@login_required
@user_passes_test(user_is_data_admin)
def master_field_edit_display_order(request):
    master_fields = MasterField.objects.order_by('name')
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
@remember_last_query_params('source-list', ['page', 'source'])
def source_list(request):
    sources = Source.objects.all()
    if len(sources) < 1:
        messages.info(
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


@login_required
@user_passes_test(user_is_data_admin)
@remember_last_query_params('master-list', ['page', 'search', 'matching', 'case-sensitive'])
def master_list(request):
    master_sources = get_master_sources()
    if len(master_sources) < 1:
        if len(Source.objects.all()) < 1:
            messages.info(
                request, "You haven't yet created any masterdata. Please import a source and then create a master from it.")
            return redirect('import-source-data')
        else:
            messages.info(
                request, "You haven't yet created any masterdata. Please pick an existing source and create masterdata from it.")
            return redirect('manage-masters')
    search = request.GET.get('search', default='').strip()
    matching = request.GET.get('matching', default='exact')
    case_sensitive = request.GET.get('case-sensitive', default='yes')
    master_fields = MasterField.objects.exclude(display_order=None)
    master_entities = get_master_entities_page(
        request, search, matching, case_sensitive)
    master_entity_data = get_master_entity_data(
        master_entities, master_fields)
    context = {
        'selection_value': request.GET.get('source'),
        'master_sources': master_sources,
        'master_fields': master_fields,
        'master_entity_data': master_entity_data,
        'page_obj': master_entities,
    }
    if search:
        context['search'] = search
        context['matching'] = matching
        context['case_sensitive'] = case_sensitive
    else:
        context['search'] = ''
        context['matching'] = 'exact'
        context['case_sensitive'] = 'yes'

    return render(request, 'masterdata/master_list.html', context)


@login_required
def master_entity_view(request, master_entity_pk):
    if request.method == 'POST':
        pass
    master_entity = MasterEntity.objects.get(pk=master_entity_pk)
    master_fields = MasterField.objects.filter(
        masterdata__master_entity=master_entity)
    source_entities = master_entity.source_entities.all()
    master_entity_data = get_separated_master_entity_data(
        master_entity, master_fields, source_entities)
    return render(request, 'masterdata/master_entity_view.html',
                  {'master_entity': master_entity,
                   'master_fields': master_fields,
                   'source_entities': source_entities,
                   'master_entity_data': master_entity_data})


@login_required
@user_passes_test(user_is_data_admin)
def master_entity_choose_edit(request, master_entity_pk, source_entity_pk):
    if request.method == 'POST':
        master_field_pk = request.POST['master_field_select']
        return redirect('master-entity-edit', master_entity_pk, source_entity_pk, master_field_pk)
    return render(request, 'masterdata/master_entity_choose_edit.html',
                  {'master_fields': MasterField.objects.all()})


@login_required
@user_passes_test(user_is_data_admin)
def master_entity_edit(request, master_entity_pk, source_entity_pk, master_field_pk):
    master_value = MasterValue.objects.filter(master_data__master_entity__pk=master_entity_pk,
                                              source_data__source_entity__pk=source_entity_pk,
                                              master_field__pk=master_field_pk).first()
    if request.method == 'POST':
        new_value = request.POST['new_value']
        old_value = master_value.value
        master_value.value = new_value
        master_value.save()
        comment = EditComment()
        comment.text = request.POST['comment']
        comment.prev_value = old_value
        comment.new_value = new_value
        comment.master_value = master_value
        comment.save()
        return redirect('master-entity-view', master_entity_pk)

    master_entity = MasterEntity.objects.get(pk=master_entity_pk)
    source_entity = SourceEntity.objects.get(pk=source_entity_pk)
    comments = master_value.editcomment_set.all()
    return render(request, 'masterdata/master_entity_edit.html',
                  {'master_value': master_value,
                   'master_entity': master_entity,
                   'source_entity': source_entity,
                   'comments': comments})


@login_required
@user_passes_test(user_is_data_admin)
def master_entity_merge(request, master_entity_pk, source_entity_pk):
    master_entity = MasterEntity.objects.get(pk=master_entity_pk)
    source_entity = SourceEntity.objects.get(pk=source_entity_pk)
    other_master_entities = MasterEntity.objects.filter(
        master_key=master_entity.master_key).exclude(pk=master_entity.pk).distinct()
    print(other_master_entities)
    if request.method == 'POST':
        new_master_entity = MasterEntity.objects.get(
            pk=request.POST['master_entity_select'])
        for data in source_entity.sourcedata_set.all():
            data.masterdata_set.clear()
        for master_field in MasterField.objects.all():
            master_value = MasterValue.objects.filter(
                master_data__master_entity=master_entity,
                source_data__source_entity=source_entity,
                master_field=master_field).first()
            new_master_data = MasterData.objects.filter(
                master_field=master_field, master_entity=new_master_entity).first()
            for data in master_value.source_data.all():
                new_master_data.source_data.add(data)
            master_value.master_data = new_master_data
            master_value.save()

        source_entity.masterentity_set.clear()
        new_master_entity.source_entities.add(source_entity)
        if len(MasterValue.objects.filter(master_data__master_entity=master_entity)) == 0:
            master_entity.delete()
        return redirect('master-list')
    return render(request, 'masterdata/master_entity_merge.html',
                  {'master_entity': master_entity,
                   'source_entity': source_entity,
                   'other_master_entities': other_master_entities})


@login_required
@user_passes_test(user_is_data_admin)
def master_entity_split(request, master_entity_pk, source_entity_pk):
    master_entity = MasterEntity.objects.get(pk=master_entity_pk)
    source_entity = SourceEntity.objects.get(pk=source_entity_pk)
    source = source_entity.source
    master_rules = json.loads(source.masterdata_rules)
    if request.method == 'POST':
        new_master_entity = MasterEntity()
        new_master_entity.source = source
        new_master_entity.master_key = get_master_key_for_source_entity(
            source_entity, master_rules)
        new_master_entity.hidden_key = len(
            source_entity.masterentity_set.all())
        new_master_entity.save()
        for data in source_entity.sourcedata_set.all():
            data.masterdata_set.clear()
        for master_field in MasterField.objects.all():
            master_value = MasterValue.objects.filter(
                master_data__master_entity=master_entity,
                source_data__source_entity=source_entity,
                master_field=master_field).first()
            master_data = MasterData()
            master_data.master_entity = new_master_entity
            master_data.master_field = master_field
            master_data.save()
            for data in master_value.source_data.all():
                master_data.source_data.add(data)
            master_value.master_data = master_data
            master_value.save()

        source_entity.masterentity_set.clear()
        new_master_entity.source_entities.add(source_entity)
        return redirect('master-list')

    return render(request, 'masterdata/master_entity_split.html',
                  {'master_entity': master_entity,
                   'source_entity': source_entity})


@login_required
@user_passes_test(user_is_data_admin)
def import_source_data(request):
    return render(request, 'masterdata/import_source_data.html')


@login_required
@user_passes_test(user_is_data_admin)
def update_existing_source(request):
    context = {'sources': Source.objects.all()}
    return render(request, 'masterdata/update_existing_source.html', context)


def save_source_file(source_file, source_name):
    upload_path = os.path.join(MEDIA_ROOT, 'source_files', source_name)
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
    with open(os.path.join(upload_path, source_file.name), 'wb+') as destination:
        for chunk in source_file.chunks():
            destination.write(chunk)


@login_required
@user_passes_test(user_is_data_admin)
def import_new_source(request, stage=1):
    if stage == 1:
        if request.method == 'POST':
            form = SourceDataImportForm(request.POST, request.FILES)
            if form.is_valid():
                source = form.save(commit=False)
                if Source.objects.filter(name=source.name).exists():
                    messages.warning(
                        request, "There exists a source with the same name. Try again.")
                    return redirect('import-new-source', 1)
                source_file = request.FILES['source_file']
                save_source_file(source_file, source.name)
                request.session['import_source'] = {
                    'name': source.name,
                    'description': source.description,
                    'reference': source.reference,
                    'source_file_path': os.path.join(MEDIA_ROOT, 'source_files', source.name, source_file.name),
                    'delimiter': source.delimiter
                }
                messages.success(
                    request, "The file was imported succesfully! Next assign the source its primary key(s).")
                return redirect('import-new-source', 2)
            return render(request, 'masterdata/import_new_source.html', {'form': form})
        form = SourceDataImportForm()
        return render(request, 'masterdata/import_new_source.html', {'form': form})
    if stage == 2:
        import_source = request.session['import_source']
        source_file_path = import_source.pop('source_file_path')
        source = Source(**import_source)
        source.source_file.name = source_file_path
        source_fields = create_source_fields(source)
        if request.method == 'POST':
            set_primary_keys(request, source_fields)
            save_data(source, source_fields)
            messages.success(
                request, "Import was successful! All the data was saved.")
            return redirect('manage-masters')

        return render(request, 'masterdata/save_new_source_data.html',
                      {'source': source,
                       'source_fields': source_fields})


def source_view(request, source_pk):
    source = Source.objects.get(pk=source_pk)
    return render(request, 'masterdata/source_view.html',
                  {'source': source})


class Echo:
    """An object that implements just the write method of the file-like
    interface.

    https://docs.djangoproject.com/en/3.1/howto/outputting-csv/
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


@login_required
def export_to_csv(request):
    """A view that streams a large CSV file."""

    search = request.GET.get('search', default='').strip()
    matching = request.GET.get('matching', default='exact')
    case_sensitive = request.GET.get('case-sensitive', default='yes')

    rows = get_rows(search, matching, case_sensitive)
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                     content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="masterdata.csv"'
    return response
