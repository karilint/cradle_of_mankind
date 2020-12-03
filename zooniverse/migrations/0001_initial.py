# Generated by Django 3.1.2 on 2020-11-16 08:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('scans', '0003_auto_20201116_0158'),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('classifications_count', models.IntegerField(null=True)),
                ('created_at', models.CharField(blank=True, max_length=255)),
                ('updated_at', models.CharField(blank=True, max_length=255)),
                ('retired_at', models.CharField(blank=True, max_length=255)),
                ('retirement_reason', models.CharField(blank=True, max_length=255)),
                ('stg_time_stamp', models.DateTimeField(null=True)),
                ('scan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='scans.scan')),
                ('workflow', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='zooniverse.workflow')),
            ],
        ),
        migrations.CreateModel(
            name='Classification',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('user_name', models.CharField(blank=True, max_length=255)),
                ('user_id', models.CharField(blank=True, max_length=255)),
                ('user_ip', models.CharField(blank=True, max_length=255)),
                ('workflow_version', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(null=True)),
                ('gold_standard', models.CharField(blank=True, max_length=255)),
                ('expert', models.CharField(blank=True, max_length=255)),
                ('meta_data', models.TextField(blank=True)),
                ('stg_time_stamp', models.DateTimeField(null=True)),
                ('workflow', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='zooniverse.workflow')),
            ],
        ),
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, unique=True)),
                ('task', models.CharField(blank=True, max_length=50)),
                ('task_label', models.TextField(blank=True)),
                ('value', models.TextField(blank=True)),
                ('stg_time_stamp', models.DateTimeField(null=True)),
                ('classification', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='zooniverse.classification')),
            ],
        ),
    ]