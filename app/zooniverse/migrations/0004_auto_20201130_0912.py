# Generated by Django 3.1.2 on 2020-11-30 07:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("scans", "0003_auto_20201116_0158"),
        ("zooniverse", "0003_auto_20201123_0532"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="subject",
            name="classification",
        ),
        migrations.RemoveField(
            model_name="subject",
            name="workflow",
        ),
        migrations.AddField(
            model_name="classification",
            name="subject",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="zooniverse.subject",
            ),
        ),
        migrations.AlterField(
            model_name="subject",
            name="scan",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="scans.scan",
            ),
        ),
    ]
