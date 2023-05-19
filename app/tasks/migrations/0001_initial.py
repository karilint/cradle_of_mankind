# Generated by Django 4.0.4 on 2022-07-30 09:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("django_celery_results", "0011_taskresult_periodic_task_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="Task",
            fields=[
                (
                    "task_id",
                    models.CharField(
                        help_text="Celery ID for the Task",
                        max_length=255,
                        unique=True,
                        verbose_name="Task ID",
                    ),
                ),
                (
                    "info",
                    models.TextField(
                        default=None,
                        editable=False,
                        help_text="JSON information about the task",
                        null=True,
                        verbose_name="Task Information",
                    ),
                ),
                (
                    "task_result",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        to="django_celery_results.taskresult",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        default=None,
                        help_text="User who started the task",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
        ),
    ]
