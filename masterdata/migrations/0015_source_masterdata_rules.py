# Generated by Django 3.1.6 on 2021-05-20 15:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0014_source_masterdata_stage'),
    ]

    operations = [
        migrations.AddField(
            model_name='source',
            name='masterdata_rules',
            field=models.TextField(default=None, null=True),
        ),
    ]
