# Generated by Django 3.1.2 on 2021-01-14 07:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_userforeignkey.models.fields


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("quality_control", "0003_annotationfield"),
    ]

    operations = [
        migrations.AddField(
            model_name="annotationfield",
            name="created_by",
            field=django_userforeignkey.models.fields.UserForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="added_annotation_fields",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="annotationfield",
            name="created_on",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="annotationfield",
            name="modified_by",
            field=django_userforeignkey.models.fields.UserForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="modified_annotation_fields",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="annotationfield",
            name="modified_on",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="finalannotation",
            name="created_by",
            field=django_userforeignkey.models.fields.UserForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="added_final_annotations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="finalannotation",
            name="created_on",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="finalannotation",
            name="modified_by",
            field=django_userforeignkey.models.fields.UserForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="modified_final_annotations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="finalannotation",
            name="modified_on",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
