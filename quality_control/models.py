from django.db import models
from zooniverse.models import Retirement
from django.db.models.deletion import CASCADE
from django.db.models.fields.related import ForeignKey, OneToOneField


class FinalAnnotation(models.Model):
    retirement = ForeignKey(Retirement, on_delete=CASCADE)
    question = models.CharField(max_length=255, blank=True)
    answer = models.TextField(blank=True)
