# Generated by Django 3.1.2 on 2020-12-18 14:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zooniverse', '0007_retirement_workflow'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='retirement',
            name='checked',
        ),
        migrations.AddField(
            model_name='retirement',
            name='status',
            field=models.CharField(default='to be checked', max_length=255),
        ),
    ]
