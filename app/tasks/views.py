import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from users.views import user_is_data_admin

from .models import Task
from django_celery_results.models import TaskResult
from cradle_of_mankind.celery import app as celery_app

import logging

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(user_is_data_admin)
def task_view(request, task_id):
    try:
        task = Task.objects.select_related("task_result").get(task_id=task_id)
    except Task.DoesNotExist:
        logger.warning(
            f'User "{request.user}" tried to access task that does not exist.'
        )
        messages.warning(
            request, "Task does not exist. Redirected back to tasks."
        )
        return redirect("task-list")
    return render(
        request,
        "tasks/task_view.html",
        {"task": task, "task_info": json.loads(task.info)},
    )


@login_required
@user_passes_test(user_is_data_admin)
def task_terminate(request, task_id):
    if request.method == "POST":
        task = Task.objects.select_related("task_result").get(task_id=task_id)
        task_info = json.loads(task.info)
        if task.task_result.status == "PENDING":
            task_result = task.task_result
            task_result.result = json.dumps(
                {
                    "exc_type": "TaskRevokedError",
                    "exc_message": ["revoked"],
                    "exc_module": "celery.exceptions",
                }
            )
            task_result.status = "REVOKED"
            task_result.save()
            celery_app.control.revoke(task_id, terminate=True)
            messages.info(
                request, f'{task_info["task_name"]} task revoked ({task_id}).'
            )
        elif task.task_result.status == "PROGRESS":
            celery_app.control.revoke(task_id, terminate=True)
            messages.info(
                request,
                f'{task_info["task_name"]} task terminated ({task_id}).',
            )
        else:
            messages.warning(
                request,
                f"Couldn't terminate task. Task was already completed.",
            )
        return redirect("task-list")
    task = Task.objects.get(task_id=task_id)
    return render(request, "tasks/task_terminate.html", {"task_id": task_id})


@login_required
@user_passes_test(user_is_data_admin)
def task_list(request):
    tasks = (
        Task.objects.select_related("task_result")
        .all()
        .order_by("-task_result__date_created")
    )
    if not tasks:
        messages.info(request, f"There are no tasks. Redirected to homepage")
        return redirect("index")
    task_ids = tasks.values_list("task_id", flat=True)
    task_info_list = tasks.values_list("info", flat=True)
    task_info = dict(
        zip(task_ids, list(map(lambda x: json.loads(x), task_info_list)))
    )
    results_list = TaskResult.objects.filter(task_id__in=task_ids)
    task_results = dict(
        zip(
            results_list.values_list("task_id", flat=True),
            list(map(lambda x: x.__dict__, results_list)),
        )
    )
    return render(
        request,
        "tasks/task_list.html",
        {"tasks": tasks, "task_info": task_info, "task_results": task_results},
    )
