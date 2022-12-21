from django.db import models
from django.conf import settings

from django_celery_results.models import TaskResult

from users.models import User


class Task(models.Model):
    task_id = models.CharField(
        max_length=getattr(
            settings, "DJANGO_CELERY_RESULTS_TASK_ID_MAX_LENGTH", 255
        ),
        unique=True,
        verbose_name="Task ID",
        help_text="Celery ID for the Task",
    )
    task_result = models.OneToOneField(
        TaskResult, on_delete=models.CASCADE, primary_key=True
    )
    user = models.ForeignKey(
        User,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name="User",
        help_text="User who started the task",
    )
    info = models.TextField(
        null=True,
        default=None,
        editable=False,
        verbose_name="Task Information",
        help_text="JSON information about the task",
    )
