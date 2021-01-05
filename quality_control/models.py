from django.db import models
from scans.models import Scan
from zooniverse.models import Retirement
from django.db.models.deletion import CASCADE
from django.db.models.fields.related import ForeignKey, OneToOneField


class FinalAnnotation(models.Model):
    scan = ForeignKey(Scan, on_delete=CASCADE)
    retirement = ForeignKey(Retirement, on_delete=CASCADE, null=True)
    question = models.CharField(max_length=255, blank=True)
    answer = models.TextField(blank=True)


class Field(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]
