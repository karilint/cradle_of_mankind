# Generated by Django 3.1.6 on 2021-05-20 07:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0012_source_master_created'),
    ]

    operations = [
        migrations.AddField(
            model_name='sourcefield',
            name='delimiters',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='sourcefield',
            name='is_divided',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sourcefield',
            name='num_of_parts',
            field=models.IntegerField(default=1),
        ),
    ]
