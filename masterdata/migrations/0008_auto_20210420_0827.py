# Generated by Django 3.1.6 on 2021-04-20 05:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0007_editcomment'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='masterfield',
            options={'ordering': ['display_order']},
        ),
        migrations.AddField(
            model_name='masterfield',
            name='display_order',
            field=models.IntegerField(default=None),
        ),
    ]
