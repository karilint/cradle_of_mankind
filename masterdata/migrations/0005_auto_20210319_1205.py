# Generated by Django 3.1.2 on 2021-03-19 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0004_auto_20210319_1149'),
    ]

    operations = [
        migrations.AlterField(
            model_name='masterfield',
            name='name',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
