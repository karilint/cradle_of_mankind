# Generated by Django 3.1.2 on 2020-12-03 10:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("zooniverse", "0004_auto_20201130_0912"),
    ]

    operations = [
        migrations.CreateModel(
            name="Retirement",
            fields=[
                (
                    "id",
                    models.IntegerField(
                        primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("classifications_count", models.IntegerField(null=True)),
                ("created_at", models.DateTimeField(null=True)),
                ("updated_at", models.DateTimeField(null=True)),
                ("retired_at", models.DateTimeField(null=True)),
                (
                    "retirement_reason",
                    models.CharField(blank=True, max_length=255),
                ),
            ],
        ),
        migrations.RemoveField(
            model_name="subject",
            name="classifications_count",
        ),
        migrations.RemoveField(
            model_name="subject",
            name="created_at",
        ),
        migrations.RemoveField(
            model_name="subject",
            name="retired_at",
        ),
        migrations.RemoveField(
            model_name="subject",
            name="retirement_reason",
        ),
        migrations.RemoveField(
            model_name="subject",
            name="updated_at",
        ),
        migrations.AddField(
            model_name="classification",
            name="retirement",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="zooniverse.retirement",
            ),
        ),
        migrations.AddField(
            model_name="subject",
            name="retirement",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="zooniverse.retirement",
            ),
        ),
    ]
