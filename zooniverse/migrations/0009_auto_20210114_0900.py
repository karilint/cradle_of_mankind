# Generated by Django 3.1.2 on 2021-01-14 07:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('zooniverse', '0008_auto_20201218_1654'),
    ]

    operations = [
        migrations.AddField(
            model_name='retirement',
            name='checked_by',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='retirement',
            name='checked_on',
            field=models.DateTimeField(default=None, null=True),
        ),
    ]