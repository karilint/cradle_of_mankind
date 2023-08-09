import json
import re
import csv
from cradle_of_mankind.settings import MEDIA_ROOT
from cradle_of_mankind.decorators import (
    remember_last_query_params,
    query_debugger,
)
from django.db import transaction
from django.db.models.functions import Cast
from django.db.models import IntegerField
from django.contrib import messages
from django.http import HttpResponse, StreamingHttpResponse
from users.views import user_is_data_admin
from tasks.models import Task
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from celery import uuid
from django_celery_results.models import TaskResult

from .forms import MasterFieldForm, SourceDataImportForm
from .tasks import (
    import_source_data,
    create_master_data,
    edit_master_data,
    delete_master,
    export_to_csv,
)
from .utils import *
from .models import (
    Source,
    SourceField,
    SourceData,
    MasterEntity,
    MasterField,
    MasterData,
    Value,
    EditComment,
    Export,
)

import logging

logger = logging.getLogger(__name__)

from django.db import connection, reset_queries


@remember_last_query_params(
    "master-list",
    [
        "page",
        "search",
        "matching",
        "case-sensitive",
        "page-size",
    ],
)
def index(request):
    master_sources = get_master_sources()
    search = request.GET.get("search", default="").strip()
    matching = request.GET.get("matching", default="exact")
    case_sensitive = request.GET.get("case-sensitive", default="yes")
    page_size = request.GET.get("page-size", default=15)
    user_level = get_user_access_level(request)
    show_table = MasterEntity.objects.count() > 0
    master_fields = MasterField.objects.filter(
        access_level__lte=user_level
    ).filter(hidden=False)
    master_entities = get_master_entities_page(
        request, search, matching, case_sensitive, page_size
    )
    master_datas = MasterData.objects.select_related("value").filter(
        master_entity__in=master_entities
    )
    master_data_dict = get_queryset_dict(
        master_datas, "master_entity_id", "master_field_id"
    )
    context = {
        "selection_value": request.GET.get("source"),
        "master_sources": master_sources,
        "master_fields": master_fields,
        "master_data_dict": master_data_dict,
        "page_obj": master_entities,
        "page_size": page_size,
        "show_table": show_table,
    }
    if search:
        context["search"] = search
        context["matching"] = matching
        context["case_sensitive"] = case_sensitive
    else:
        context["search"] = ""
        context["matching"] = "exact"
        context["case_sensitive"] = "yes"
    return render(request, "masterdata/masterdata-index.html", context)


@login_required
@user_passes_test(user_is_data_admin)
def manage_masters(request):
    sources = Source.objects.all()
    if len(sources) < 1:
        messages.info(
            request,
            "You haven't yet added any sources. Please import one first.",
        )
        return redirect("import-source-data")
    return render(
        request, "masterdata/manage_masters.html", {"sources": sources}
    )


@login_required
@user_passes_test(user_is_data_admin)
@transaction.atomic
def create_master(request, source_pk, stage):
    source = Source.objects.get(pk=source_pk)
    source_fields = source.source_fields.all()
    title = "Create Master"

    if stage == 1:
        if request.method == "POST":
            stage1_post(request, source, source_fields, stage)
            return redirect("create-master", source_pk, stage + 1)
        examples = create_examples(source)
        instructions = "Stage 1/4: Choose which fields need to be divided into parts and how many masters are they mapped to."
        return render(
            request,
            "masterdata/create_master_stage1.html",
            {
                "title": title,
                "instructions": instructions,
                "source": source,
                "source_fields": source_fields,
                "examples": examples,
            },
        )

    elif stage == 2:
        source_fields = source_fields.filter(is_divided=True)
        if request.method == "POST":
            stage2_post(request, source, source_fields, stage)
            next_stage = stage + 1 if "next" in request.POST else stage - 1
            return redirect("create-master", source_pk, next_stage)
        examples = create_examples(source)
        instructions = "Stage 2/4: Give delimiters that will be used to divide the source fields you want to be in masterdata."
        return render(
            request,
            "masterdata/create_master_stage2.html",
            {
                "title": title,
                "instructions": instructions,
                "source": source,
                "source_fields": source_fields,
                "examples": examples,
            },
        )

    elif stage == 3:
        master_fields = MasterField.objects.all()
        if request.method == "POST":
            masterdata_rules = {}
            for master_field in master_fields:
                masterdata_rules[str(master_field.id)] = {}
            stage3_post(
                request, source, source_fields, masterdata_rules, stage
            )
            next_stage = stage + 1 if "next" in request.POST else stage - 1
            return redirect("create-master", source_pk, next_stage)
        selection_rules = get_selection_rules(source, master_fields)
        examples = create_examples_with_parts(source)
        instructions = "Stage 3/4: Assign rules for master field mapping."
        return render(
            request,
            "masterdata/create_master_stage3.html",
            {
                "title": title,
                "instruction": instructions,
                "source": source,
                "source_fields": source_fields,
                "master_fields": master_fields,
                "rules": selection_rules,
                "examples": examples,
            },
        )

    elif stage == 4:
        if request.method == "POST":
            task_id = uuid()
            task_name = "Masterdata Creation"
            user = request.user
            info = {"task_name": task_name}
            task_result = TaskResult.objects.create(
                task_id=task_id, task_name=task_name
            )
            task = Task.objects.create(
                task_id=task_id,
                task_result=task_result,
                user=user,
                info=json.dumps(info),
            )
            create_master_data.apply_async((source.id,), task_id=task_id)
            return redirect("task-view", task_id)
        master_fields = MasterField.objects.all()
        example_table = create_example_table(source)
        instructions = "Stage 4/4: Sample rows with given rules. Looks good?"
        return render(
            request,
            "masterdata/create_master_stage4.html",
            {
                "title": title,
                "instructions": instructions,
                "source": source,
                "master_fields": master_fields,
                "example_table": example_table,
            },
        )


@login_required
@user_passes_test(user_is_data_admin)
@query_debugger
def edit_master(request, source_pk, stage):
    source = Source.objects.get(pk=source_pk)
    source_fields = (
        SourceField.objects.filter(source=source)
        .filter(source_datas__master_datas=None)
        .distinct()
    )
    title = "Edit Master"
    if stage == 1:
        if request.method == "POST":
            stage1_post(request, source, source_fields, stage)
            return redirect("edit-master", source_pk, stage + 1)
        examples = create_examples(source)
        instructions = (
            "Stage 1/4: Choose which fields need to be divided into parts "
            "(only the fields that haven't been mapped yet are shown)."
        )
        return render(
            request,
            "masterdata/create_master_stage1.html",
            {
                "title": title,
                "instructions": instructions,
                "source": source,
                "source_fields": source_fields,
                "examples": examples,
            },
        )
    elif stage == 2:
        source_fields = source_fields.filter(is_divided=True)
        if request.method == "POST":
            stage2_post(request, source, source_fields, stage)
            next_stage = stage + 1 if "next" in request.POST else stage - 1
            return redirect("edit-master", source_pk, next_stage)
        examples = create_examples(source)
        instructions = "Stage 2/4: Give delimiters that will be used to divide the source fields you want to be in masterdata."
        return render(
            request,
            "masterdata/create_master_stage2.html",
            {
                "title": title,
                "instructions": instructions,
                "source": source,
                "source_fields": source_fields,
                "examples": examples,
            },
        )
    elif stage == 3:
        master_fields = MasterField.objects.exclude(
            master_datas__source_datas__source_entity__source=source
        )
        if request.method == "POST":
            if source.masterdata_rules:
                masterdata_rules = json.loads(source.masterdata_rules)
            stage3_post(
                request, source, source_fields, masterdata_rules, stage
            )
            next_stage = stage + 1 if "next" in request.POST else stage - 1
            return redirect("edit-master", source_pk, next_stage)
        selection_rules = get_selection_rules(source, master_fields)
        examples = create_examples_with_parts(source)
        instructions = "Stage 3/4: Assign rules for master field mapping."
        return render(
            request,
            "masterdata/create_master_stage3.html",
            {
                "title": title,
                "instruction": instructions,
                "source": source,
                "source_fields": source_fields,
                "master_fields": master_fields,
                "rules": selection_rules,
                "examples": examples,
            },
        )
    elif stage == 4:
        if request.method == "POST":
            task_id = uuid()
            task_name = "Masterdata Edit"
            user = request.user
            info = {"task_name": task_name}
            task_result = TaskResult.objects.create(
                task_id=task_id, task_name=task_name
            )
            task = Task.objects.create(
                task_id=task_id,
                task_result=task_result,
                user=user,
                info=json.dumps(info),
            )
            edit_master_data.apply_async((source.id,), task_id=task_id)
            return redirect("task-view", task_id)
        if request.method == "POST":
            master_rules = json.loads(source.masterdata_rules)
            master_fields = MasterField.objects.exclude(sources=source)
            for source_entity in source.source_entities.all():
                master_entity = MasterEntity.objects.get(
                    source_entity=source_entity
                )
            stage4_post(
                source,
                source_entity,
                master_entity,
                master_fields,
                master_rules,
            )
            source.master_created = True
            source.save()
            return redirect("manage-masters")
        master_fields = MasterField.objects.all()
        example_table = create_example_table(source)
        instructions = "Stage 4/4: Sample rows with given rules. Looks good?"
        return render(
            request,
            "masterdata/create_master_stage4.html",
            {
                "title": title,
                "instructions": instructions,
                "source": source,
                "master_fields": master_fields,
                "example_table": example_table,
            },
        )


@login_required
@user_passes_test(user_is_data_admin)
def delete_master_view(request, source_pk):
    source = Source.objects.get(pk=source_pk)
    if request.method == "POST":
        task_id = uuid()
        task_name = "Master deletion"
        user = request.user
        info = {"task_name": task_name}
        task_result = TaskResult.objects.create(
            task_id=task_id, task_name=task_name
        )
        task = Task.objects.create(
            task_id=task_id,
            task_result=task_result,
            user=user,
            info=json.dumps(info),
        )
        delete_master.apply_async((source.id,), task_id=task_id)
        return redirect("task-view", task_id)
    return render(request, "masterdata/delete_master.html", {"source": source})


@login_required
@user_passes_test(user_is_data_admin)
def master_fields(request):
    if request.method == "POST":
        form = MasterFieldForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "The field was added succesfully.")
            return redirect("master-fields")
        else:
            messages.error(
                request,
                "Cannot add that field. Did you try to add a field that already exists?",
            )
    master_fields = MasterField.objects.all()
    form = MasterFieldForm()
    return render(
        request,
        "masterdata/master_fields.html",
        {"master_fields": master_fields, "form": form},
    )


@login_required
@user_passes_test(user_is_data_admin)
def master_field_edit(request, master_field_pk):
    master_field = MasterField.objects.get(pk=master_field_pk)
    if request.method == "POST":
        form = MasterFieldForm(
            request.POST,
            instance=master_field,
            initial={
                "name": master_field.name,
                "description": master_field.description,
                "primary_key": master_field.primary_key,
            },
        )

        if form.is_valid():
            form.save()
            messages.success(request, "The master field has been updated!")
            return redirect("master-fields")
    else:
        form = MasterFieldForm(instance=master_field)
    return render(
        request,
        "masterdata/master_field_edit.html",
        {"form": form, "master_field": master_field},
    )


@login_required
@user_passes_test(user_is_data_admin)
def master_field_delete(request, master_field_pk):
    master_field = MasterField.objects.get(pk=master_field_pk)
    if request.method == "POST":
        if master_field.master_datas.count() == 0:
            master_field.delete()
            messages.success(
                request, "The master field was deleted succesfully!"
            )
        else:
            messages.warning(
                request,
                "The master field could not be deleted. There is some master data using it!",
            )
        return redirect("master-fields")
    return render(
        request,
        "masterdata/master_field_delete.html",
        {"master_field": master_field},
    )


@login_required
@user_passes_test(user_is_data_admin)
def master_field_edit_display_order(request):
    master_fields = MasterField.objects.order_by("name")
    if request.method == "POST":
        for field in master_fields:
            new_value = request.POST[field.name]
            if new_value == "0":
                field.display_order = None
            else:
                field.display_order = int(new_value)
            field.save()
        return redirect("master-fields")
    options = list(range(1, len(master_fields) + 1))
    current_display_orders = {}
    for field in master_fields:
        current_display_orders[field.name] = field.display_order
    return render(
        request,
        "masterdata/master_field_edit_display_order.html",
        {
            "master_fields": master_fields,
            "options": options,
            "current_display_orders": current_display_orders,
        },
    )


@login_required
@user_passes_test(user_is_data_admin)
@remember_last_query_params("source-list", ["page", "source", "page-size"])
def source_list(request):
    sources = Source.objects.all()
    if len(sources) < 1:
        messages.info(
            request,
            "You haven't yet added any sources. Please import one first.",
        )
        return redirect("import-source-data")
    source = get_source(request)
    source_fields = SourceField.objects.filter(source=source)
    page_size = request.GET.get("page-size", default=15)
    source_entities = get_source_entities(request, source, page_size)
    source_entity_data = get_source_entity_data(source_entities, source_fields)
    return render(
        request,
        "masterdata/source_list.html",
        {
            "selected_source": source,
            "sources": sources,
            "source_fields": source_fields,
            "source_entity_data": source_entity_data,
            "page_obj": source_entities,
            "page_size": page_size,
        },
    )


@login_required
@user_passes_test(user_is_data_admin)
@remember_last_query_params(
    "master-list",
    [
        "page",
        "search",
        "matching",
        "case-sensitive",
        "page-size",
    ],
)
def master_list(request):
    master_sources = get_master_sources()
    if len(master_sources) < 1:
        if len(Source.objects.all()) < 1:
            messages.info(
                request,
                "You haven't yet created any masterdata. Please import a source and then create a master from it.",
            )
            return redirect("import-source-data")
        else:
            messages.info(
                request,
                "You haven't yet created any masterdata. Please pick an existing source and create masterdata from it.",
            )
            return redirect("manage-masters")
    search = request.GET.get("search", default="").strip()
    matching = request.GET.get("matching", default="exact")
    case_sensitive = request.GET.get("case-sensitive", default="yes")
    page_size = request.GET.get("page-size", default=15)
    user_level = get_user_access_level(request)
    master_fields = MasterField.objects.filter(
        access_level__lte=user_level
    ).filter(hidden=False)
    master_entities = get_master_entities_page(
        request, search, matching, case_sensitive, page_size
    )
    master_datas = MasterData.objects.select_related("value").filter(
        master_entity__in=master_entities
    )
    master_data_dict = get_queryset_dict(
        master_datas, "master_entity_id", "master_field_id"
    )
    context = {
        "selection_value": request.GET.get("source"),
        "master_sources": master_sources,
        "master_fields": master_fields,
        "master_data_dict": master_data_dict,
        "page_obj": master_entities,
        "page_size": page_size,
    }
    if search:
        context["search"] = search
        context["matching"] = matching
        context["case_sensitive"] = case_sensitive
    else:
        context["search"] = ""
        context["matching"] = "exact"
        context["case_sensitive"] = "yes"
    return render(request, "masterdata/master_list.html", context)


@login_required
def master_entity_view(request, master_entity_pk):
    if request.method == "POST":
        pass
    master_entity = MasterEntity.objects.get(pk=master_entity_pk)
    user_level = get_user_access_level(request)
    master_fields = (
        MasterField.objects.filter(master_datas__master_entity=master_entity)
        .filter(access_level__lte=user_level)
        .distinct()
    )
    source_entities = (
        SourceEntity.objects.select_related("source")
        .filter(source_datas__master_datas__master_entity=master_entity)
        .distinct()
    )
    master_datas = (
        MasterData.objects.select_related("value")
        .filter(source_datas__source_entity__in=source_entities)
        .annotate(
            source_entity_id=Cast(
                "source_datas__source_entity__id", output_field=IntegerField()
            ),
        )
        .distinct()
    )
    master_data_dict = get_queryset_dict(
        master_datas, "source_entity_id", "master_field_id"
    )
    return render(
        request,
        "masterdata/master_entity_view.html",
        {
            "master_entity": master_entity,
            "master_fields": master_fields,
            "source_entities": source_entities,
            "master_data_dict": master_data_dict,
        },
    )


@login_required
@user_passes_test(user_is_data_admin)
def master_entity_choose_edit(request, master_entity_pk, source_entity_pk):
    if request.method == "POST":
        master_field_pk = request.POST["master_field_select"]
        return redirect(
            "master-entity-edit",
            master_entity_pk,
            source_entity_pk,
            master_field_pk,
        )
    return render(
        request,
        "masterdata/master_entity_choose_edit.html",
        {"master_fields": MasterField.objects.all()},
    )


@login_required
@user_passes_test(user_is_data_admin)
def master_entity_edit(
    request, master_entity_pk, source_entity_pk, master_field_pk
):
    master_data = (
        MasterData.objects.select_related("value")
        .filter(master_entity__id=master_entity_pk)
        .filter(master_field__id=master_field_pk)
        .filter(source_datas__source_entity__id=source_entity_pk)
        .distinct()
        .get()
    )
    if request.method == "POST":
        with transaction.atomic():
            try:
                new_value = Value.objects.get(value=request.POST["new_value"])
            except Value.DoesNotExist:
                new_value = Value.objects.create(request.POST["new_value"])
            prev_value = master_data.value
            master_data.value = new_value
            master_data.save()
            comment = EditComment()
            comment.text = request.POST["comment"]
            comment.prev_value = prev_value
            comment.new_value = new_value
            comment.master_data = master_data
            comment.user = request.user
            comment.save()
        return redirect("master-entity-view", master_entity_pk)
    comments = master_data.edit_comments.select_related(
        "prev_value", "new_value"
    ).all()
    return render(
        request,
        "masterdata/master_entity_edit.html",
        {
            "master_data": master_data,
            "master_entity_pk": master_entity_pk,
            "comments": comments,
        },
    )


@login_required
@user_passes_test(user_is_data_admin)
def master_entity_merge(request, master_entity_pk, source_entity_pk):
    if request.method == "POST":
        new_master_entity = MasterEntity.objects.get(
            pk=request.POST["master_entity_select"]
        )
        master_datas = (
            MasterData.objects.filter(master_entity__id=master_entity_pk)
            .filter(source_datas__source_entity__id=source_entity_pk)
            .distinct()
        )
        for master_data in master_datas:
            master_data.master_entity = new_master_entity
        with transaction.atomic():
            MasterData.objects.bulk_update(master_datas, ["master_entity"])
            if (
                MasterData.objects.filter(
                    master_entity__id=master_entity_pk
                ).count()
                == 0
            ):
                MasterEntity.objects.filter(pk=master_entity_pk).delete()
        return redirect("master-list")
    master_entity = MasterEntity.objects.get(pk=master_entity_pk)
    other_master_entities = (
        MasterEntity.objects.filter(master_key=master_entity.master_key)
        .exclude(pk=master_entity.pk)
        .distinct()
    )
    return render(
        request,
        "masterdata/master_entity_merge.html",
        {
            "master_entity": master_entity,
            "other_master_entities": other_master_entities,
        },
    )


@login_required
@user_passes_test(user_is_data_admin)
def master_entity_split(request, master_entity_pk, source_entity_pk):
    if request.method == "POST":
        master_entity = MasterEntity.objects.get(pk=master_entity_pk)
        source_entity = SourceEntity.objects.select_related("source").get(
            pk=source_entity_pk
        )
        master_datas = (
            MasterData.objects.filter(master_entity__id=master_entity_pk)
            .filter(source_datas__source_entity__id=source_entity_pk)
            .distinct()
        )
        master_rules = json.loads(source_entity.source.masterdata_rules)
        new_master_entity = MasterEntity()
        new_master_entity.master_key = get_master_key_for_source_entity(
            source_entity, master_rules
        )
        new_master_entity.hidden_key = get_hidden_key(new_master_entity)
        with transaction.atomic():
            new_master_entity.save()
            for master_data in master_datas:
                master_data.master_entity = new_master_entity
            MasterData.objects.bulk_update(master_datas, ["master_entity"])
        return redirect("master-entity-view", master_entity_pk)
    return render(
        request,
        "masterdata/master_entity_split.html",
        {"master_entity_pk": master_entity_pk},
    )


@login_required
@user_passes_test(user_is_data_admin)
def import_source_data_view(request):
    return render(request, "masterdata/import_source_data.html")


@login_required
@user_passes_test(user_is_data_admin)
def update_existing_source(request):
    context = {"sources": Source.objects.all()}
    return render(request, "masterdata/update_existing_source.html", context)


def save_source_file(source_file, source_name):
    upload_path = os.path.join(MEDIA_ROOT, "source_files", source_name)
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
    with open(
        os.path.join(upload_path, source_file.name), "wb+"
    ) as destination:
        for chunk in source_file.chunks():
            destination.write(chunk)


@login_required
@user_passes_test(user_is_data_admin)
def import_new_source(request, stage=1):
    if stage == 1:
        if request.method == "POST":
            form = SourceDataImportForm(request.POST, request.FILES)
            if form.is_valid():
                source = form.save(commit=False)
                if Source.objects.filter(name=source.name).exists():
                    messages.warning(
                        request,
                        "There exists a source with the same name. Try again.",
                    )
                    return redirect("import-new-source", 1)
                source_file = request.FILES["source_file"]
                save_source_file(source_file, source.name)
                request.session["source_import"] = {
                    "name": source.name,
                    "description": source.description,
                    "reference": source.reference,
                    "source_file_path": os.path.join(
                        MEDIA_ROOT,
                        "source_files",
                        source.name,
                        source_file.name,
                    ),
                    "delimiter": source.delimiter,
                }
                messages.success(
                    request,
                    "The file was imported succesfully! Next assign the source its primary key(s).",
                )
                return redirect("import-new-source", 2)
            return render(
                request, "masterdata/import_new_source.html", {"form": form}
            )
        form = SourceDataImportForm()
        return render(
            request, "masterdata/import_new_source.html", {"form": form}
        )
    if stage == 2:
        source_import = request.session["source_import"]
        if request.method == "POST":
            task_id = uuid()
            task_name = "Source Data Import"
            user = request.user
            info = {"task_name": task_name}
            task_result = TaskResult.objects.create(
                task_id=task_id, task_name=task_name
            )
            task = Task.objects.create(
                task_id=task_id,
                task_result=task_result,
                user=user,
                info=json.dumps(info),
            )
            import_source_data.apply_async(
                (source_import, request.POST), task_id=task_id
            )
            return redirect("task-view", task_id)
        source_file_path = source_import.pop("source_file_path")
        source = Source(**source_import)
        source.source_file.name = source_file_path
        source_fields = create_source_fields(source)
        return render(
            request,
            "masterdata/save_new_source_data.html",
            {"source": source, "source_fields": source_fields},
        )


def source_view(request, source_pk):
    source = Source.objects.get(pk=source_pk)
    return render(request, "masterdata/source_view.html", {"source": source})


class Echo:
    """An object that implements just the write method of the file-like
    interface.

    https://docs.djangoproject.com/en/3.1/howto/outputting-csv/
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


@login_required
def export_masterdata(request):
    search = request.GET.get("search", default="").strip()
    matching = request.GET.get("matching", default="exact")
    case_sensitive = request.GET.get("case-sensitive", default="yes")

    task_id = uuid()
    task_name = "Masterdata export"
    user = request.user
    info = {
        "task_name": task_name,
        "export_status": "PENDING",
    }
    task_result = TaskResult.objects.create(
        task_id=task_id, task_name=task_name
    )
    task = Task.objects.create(
        task_id=task_id,
        task_result=task_result,
        user=user,
        info=json.dumps(info),
    )
    new_export = Export()
    new_export.task = task
    new_export.user = request.user
    new_export.status = Export.Status.PENDING
    new_export.search = search
    new_export.matching = matching
    new_export.case_sensitive = True if case_sensitive == "yes" else False
    new_export.save()

    export_to_csv.apply_async(
        (user.id, search, matching, case_sensitive),
        task_id=task_id,
    )
    return redirect("export-view", new_export.id)


@login_required
def export_view(request, export_pk):
    export = Export.objects.get(pk=export_pk)
    if export.user != request.user:
        return redirect("export")
    task = Task.objects.select_related("task_result").get(
        task_id=export.task.task_id
    )
    context = {
        "export": export,
        "task": task,
        "task_info": json.loads(task.info),
    }
    return render(request, "masterdata/export_view.html", context)
