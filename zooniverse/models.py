from django.db import models
from django.db.models.fields.related import ForeignKey, OneToOneField
from scans.models import Scan


class Workflow(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    name = models.CharField(max_length=255)


class Retirement(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    classifications_count = models.IntegerField(null=True)
    created_at = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(null=True)
    retired_at = models.DateTimeField(null=True)
    retirement_reason = models.CharField(max_length=255, blank=True)


class Subject(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    scan = OneToOneField(Scan, on_delete=models.SET_NULL, null=True)
    retirement = models.ForeignKey(Retirement, models.SET_NULL,
                                   blank=True, null=True)


class Classification(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    user_name = models.CharField(max_length=255, blank=True)
    user_id = models.CharField(max_length=255, blank=True)
    user_ip = models.CharField(max_length=255, blank=True)
    subject = models.ForeignKey(Subject, models.SET_NULL,
                                blank=True, null=True)
    retirement = models.ForeignKey(Retirement, models.SET_NULL,
                                   blank=True, null=True)
    workflow = models.ForeignKey(Workflow, models.SET_NULL,
                                 blank=True, null=True)
    workflow_version = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(null=True)
    gold_standard = models.CharField(max_length=255, blank=True)
    expert = models.CharField(max_length=255, blank=True)
    meta_data = models.TextField(blank=True)


class Annotation(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    classification = models.ForeignKey(
        Classification, on_delete=models.SET_NULL, null=True)
    task = models.CharField(max_length=50, blank=True)
    task_label = models.TextField(blank=True)
    value = models.TextField(blank=True)

    class Meta:
        unique_together = [['classification', 'task']]
