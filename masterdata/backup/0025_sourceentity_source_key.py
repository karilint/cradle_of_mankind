# Generated by Django 3.1.6 on 2021-07-16 09:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0024_auto_20210716_0857'),
    ]

    operations = [
        migrations.AddField(
            model_name='sourceentity',
            name='source_key',
            field=models.CharField(default=None, max_length=255, null=True),
        ),
    ]
