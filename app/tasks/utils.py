from django_celery_results.models import TaskResult
from celery_progress.backend import ProgressRecorder


def set_task_state(task, state):
    task_id = task.request.id
    task_result = TaskResult.objects.get(task_id=task_id)
    task_result.status = state
    task_result.save()


def record_progress(task, current, total, interval=1, description=""):
    if current % interval != 0 and current != total:
        return
    progress_recorder = ProgressRecorder(task)
    progress_recorder.set_progress(current, total, description)


