# Generated by Django 3.1.6 on 2021-05-20 07:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0013_auto_20210520_1017'),
    ]

    operations = [
        migrations.AddField(
            model_name='source',
            name='masterdata_stage',
            field=models.IntegerField(default=0),
        ),
    ]
