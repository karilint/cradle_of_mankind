import os
import json

from users.views import user_is_data_admin

from django.contrib import messages
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import DataImportForm

from celery import uuid
from django_celery_results.models import TaskResult
from .tasks import update_zooniverse_data
from .utils import check_imported_files

from tasks.models import Task


def save_uploaded_file(f):
    try:
        os.mkdir(os.path.join(settings.MEDIA_ROOT, "imports"))
    except:
        pass

    path_to_file = os.path.join(settings.MEDIA_ROOT, "imports", f.name)
    with open(path_to_file, "wb+") as destination:
        for chunk in f.chunks():
            destination.write(chunk)


@login_required
@user_passes_test(user_is_data_admin)
def import_data(request):
    if request.method == "POST" and "btn-upload" in request.POST:
        form = DataImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES["file"]
            save_uploaded_file(f)
    elif request.method == "POST" and "btn-update-db" in request.POST:
        success = check_imported_files()
        if not success:
            messages.warning(
                request,
                "Update couldn't start. Have you uploaded all the required files? (specimen-numbers-classifications.csv, location-and-stratigraphy-classifications.csv, additional-info-card-backside-classifications.csv, specimen-taxonomy-latin-names-classifications.csv, nature-of-specimen-body-parts-classifications.csv)",
            )
            return redirect("import-data")
        task_id = uuid()
        task_name = "Zooniverse Import"
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
        update_zooniverse_data.apply_async((), task_id=task_id)
        return redirect("task-view", task_id)
    form = DataImportForm()
    return render(request, "zooniverse/zooniverse_import.html", {"form": form})
