# Generated by Django 3.1.2 on 2020-12-21 20:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("scans", "0003_auto_20201116_0158"),
        ("zooniverse", "0008_auto_20201218_1654"),
        ("quality_control", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="finalannotation",
            name="scan",
            field=models.ForeignKey(
                default="1",
                on_delete=django.db.models.deletion.CASCADE,
                to="scans.scan",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="finalannotation",
            name="retirement",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="zooniverse.retirement",
            ),
        ),
    ]
