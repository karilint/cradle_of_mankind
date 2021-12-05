from django.db import models
from django.db.models.deletion import PROTECT
from django.db.models.fields.files import ImageField
from django_userforeignkey.models.fields import UserForeignKey
from simple_history.models import HistoricalRecords


class Scan(models.Model):
    image = ImageField(upload_to='scans', null=True)
    type = models.CharField(max_length=50)
    text = models.TextField()
    status = models.CharField(max_length=25)
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    created_by = UserForeignKey(auto_user_add=True, on_delete=PROTECT,
                                related_name='added_scans')
    modified_by = UserForeignKey(auto_user=True, on_delete=PROTECT,
                                 related_name='modified_scans')
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
        inherit=True)
