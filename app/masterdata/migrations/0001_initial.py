# Generated by Django 4.0.7 on 2022-10-07 08:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import masterdata.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MasterData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'default_related_name': 'master_datas',
            },
        ),
        migrations.CreateModel(
            name='MasterEntity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('master_key', models.CharField(max_length=255)),
                ('hidden_key', models.IntegerField(default=None, null=True)),
            ],
            options={
                'ordering': ['master_key'],
                'default_related_name': 'master_entities',
            },
        ),
        migrations.CreateModel(
            name='MasterField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('abbreviation', models.CharField(blank=True, default='', max_length=255)),
                ('primary_key', models.BooleanField(default=False)),
                ('display_order', models.IntegerField(default=None, null=True)),
                ('description', models.TextField(blank=True)),
                ('access_level', models.IntegerField(choices=[(1, 'Guest'), (2, 'Registered'), (3, 'Editor'), (4, 'Data Admin')], default=1)),
            ],
            options={
                'ordering': ['display_order'],
                'default_related_name': 'master_fields',
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True, default='')),
                ('reference', models.TextField(blank=True, default='')),
                ('source_file', models.FileField(upload_to=masterdata.models.Source.name_based_upload)),
                ('delimiter', models.CharField(max_length=10)),
                ('master_created', models.BooleanField(default=False)),
                ('masterdata_stage', models.IntegerField(default=0)),
                ('masterdata_rules', models.TextField(default=None, null=True)),
            ],
            options={
                'default_related_name': 'sources',
            },
        ),
        migrations.CreateModel(
            name='Value',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField()),
            ],
            options={
                'default_related_name': 'values',
            },
        ),
        migrations.CreateModel(
            name='SourceField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('is_primary_key', models.BooleanField(default=False)),
                ('display_order', models.IntegerField()),
                ('is_divided', models.BooleanField(default=False)),
                ('delimiters', models.CharField(blank=True, default='', max_length=255)),
                ('num_of_parts', models.IntegerField(default=1)),
                ('num_of_mappings', models.IntegerField(default=1)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.source')),
            ],
            options={
                'ordering': ['display_order'],
                'default_related_name': 'source_fields',
            },
        ),
        migrations.CreateModel(
            name='SourceEntity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_key', models.CharField(default=None, max_length=255, null=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.source')),
            ],
            options={
                'default_related_name': 'source_entities',
            },
        ),
        migrations.CreateModel(
            name='SourceData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.sourceentity')),
                ('source_field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.sourcefield')),
                ('value', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='masterdata.value')),
            ],
            options={
                'default_related_name': 'source_datas',
            },
        ),
        migrations.CreateModel(
            name='MasterSourceData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('master_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.masterdata')),
                ('source_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.sourcedata')),
            ],
        ),
        migrations.AddField(
            model_name='masterdata',
            name='master_entity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.masterentity'),
        ),
        migrations.AddField(
            model_name='masterdata',
            name='master_field',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.masterfield'),
        ),
        migrations.AddField(
            model_name='masterdata',
            name='source_datas',
            field=models.ManyToManyField(through='masterdata.MasterSourceData', to='masterdata.sourcedata'),
        ),
        migrations.AddField(
            model_name='masterdata',
            name='value',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='masterdata.value'),
        ),
        migrations.CreateModel(
            name='EditComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(blank=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('master_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.masterdata')),
                ('new_value', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='new_value_comments', to='masterdata.value')),
                ('prev_value', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='prev_value_comments', to='masterdata.value')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'default_related_name': 'edit_comments',
            },
        ),
    ]
