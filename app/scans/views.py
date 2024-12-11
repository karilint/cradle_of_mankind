import json
import logging
import os

from pathlib import Path
from celery import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models.query_utils import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import DetailView, ListView, UpdateView
from django_celery_results.models import TaskResult

from cradle_of_mankind.settings import MEDIA_ROOT
from tasks.models import Task
from users.views import user_is_data_admin

from .forms import ScanDataImportForm, ScanEditForm
from .models import Scan
from .tasks import create_blank_scan_objects, save_scan_data

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(user_is_data_admin)
def import_scan_images(request):
    if request.method == "POST":
        images = request.FILES.getlist("images")
        scans_path = os.path.join(MEDIA_ROOT, "scans")
        Path(scans_path).mkdir(parents=True, exist_ok=True)
        for image in images:
            destination = open(os.path.join(scans_path, image.name), "wb+")
            for chunk in image.chunks():
                destination.write(chunk)
            destination.close()
        messages.success(request, "Images uploaded succesfully")
        return redirect("scan-list")
    return render(request, "scans/import_scan_images.html")


class ScanListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Scan
    template_name = "scan_list.html"
    context_object_name = "scans"
    paginate_by = 10

    def test_func(self):
        user = self.request.user
        return user.is_data_admin or user.is_editor


class ScanSearchView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Scan
    template_name = "scans/scan_search.html"
    context_object_name = "scans"
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get("query")
        type = self.request.GET.get("type")
        status = self.request.GET.get("status")
        if type == "":
            scan_list = Scan.objects.filter(
                Q(type__icontains=type),
                Q(status__icontains=status),
                Q(id__iexact=query) | Q(text__icontains=query),
            )
        else:
            scan_list = Scan.objects.filter(
                Q(type__iexact=type),
                Q(status__icontains=status),
                Q(id__iexact=query) | Q(text__icontains=query),
            )
        return scan_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("query")
        context["type"] = self.request.GET.get("type")
        context["status"] = self.request.GET.get("status")
        context["whole_query"] = (
            f"?query={context['query']}&type={context['type']}&status={context['status']}"
        )
        return context

    def test_func(self):
        user = self.request.user
        return user.is_data_admin or user.is_editor


class ScanDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Scan

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scan = context["scan"]
        image_exists = True
        try:
            with open(scan.image.path, "r") as img:
                print("image found")
        except FileNotFoundError as e:
            image_exists = False
            print("image not found")

        context["image_exists"] = image_exists
        return context

    def test_func(self):
        user = self.request.user
        return user.is_data_admin or user.is_editor


class ScanEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Scan
    form_class = ScanEditForm
    context_object_name = "scan"

    def get_success_url(self):
        return reverse("scan-detail", kwargs={"pk": self.object.pk})

    def test_func(self):
        user = self.request.user
        return user.is_data_admin or user.is_editor


@login_required
@user_passes_test(user_is_data_admin)
def import_scans(request):
    scans_path = os.path.join(MEDIA_ROOT, "scans")
    Path(scans_path).mkdir(parents=True, exist_ok=True)
    scan_images = os.listdir(scans_path)
    scan_image_ids = set(map(lambda i: int(i.split(".")[0]), scan_images))
    scan_object_ids = set(Scan.objects.all().values_list("id", flat=True))
    missing_scan_object_ids = scan_image_ids - scan_object_ids
    if request.method == "POST" and "btn-add-blanks" in request.POST:
        logger.info("Starting the task of creating blank scan objects")
        task_id = uuid()
        task_name = "Create Blank Scan Objects"
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
        create_blank_scan_objects.apply_async(
            (list(missing_scan_object_ids), user.id), task_id=task_id
        )
        return redirect("task-view", task_id)
    elif request.method == "POST":
        form = ScanDataImportForm(request.POST, request.FILES)
        if form.is_valid():
            scan_data = json.load(request.FILES["file"])
            task_id = uuid()
            task_name = "Scan Import"
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
            save_scan_data.apply_async((scan_data, user.id), task_id=task_id)
            return redirect("task-view", task_id)
    form = ScanDataImportForm()
    return render(
        request,
        "scans/scan_import.html",
        {
            "form": form,
            "missing_scan_data_count": len(missing_scan_object_ids),
        },
    )
