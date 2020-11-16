from django.db import models
from django.db.models.fields.related import ForeignKey
from scans.models import Scan


class Workflow(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    name = models.CharField(max_length=255)


class Classification(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    user_name = models.CharField(max_length=255, blank=True)
    user_id = models.CharField(max_length=255, blank=True)
    user_ip = models.CharField(max_length=255, blank=True)
    workflow = models.ForeignKey(Workflow, models.SET_NULL,
                                 blank=True, null=True)
    workflow_version = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(null=True)
    gold_standard = models.CharField(max_length=255, blank=True)
    expert = models.CharField(max_length=255, blank=True)
    meta_data = models.TextField(blank=True)
    stg_time_stamp = models.DateTimeField(null=True)


class Annotation(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    classification = models.ForeignKey(
        Classification, on_delete=models.SET_NULL, null=True)
    task = models.CharField(max_length=50, blank=True)
    task_label = models.TextField(blank=True)
    value = models.TextField(blank=True)
    stg_time_stamp = models.DateTimeField(null=True)

    class Meta:
        unique_together = [['classification', 'task']]


class Subject(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    scan = ForeignKey(Scan, on_delete=models.SET_NULL,
                      blank=True, null=True)
    workflow = ForeignKey(Workflow, on_delete=models.SET_NULL,
                          blank=True, null=True)
    classification = models.OneToOneField(
        Classification, on_delete=models.SET_NULL, null=True)
    classifications_count = models.IntegerField(null=True)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    retired_at = models.CharField(max_length=255, blank=True)
    retirement_reason = models.CharField(max_length=255, blank=True)
    stg_time_stamp = models.DateTimeField(null=True)
