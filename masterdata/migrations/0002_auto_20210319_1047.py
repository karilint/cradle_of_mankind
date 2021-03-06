# Generated by Django 3.1.2 on 2021-03-19 08:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MasterField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.AlterModelOptions(
            name='sourcefield',
            options={'ordering': ['display_order']},
        ),
        migrations.CreateModel(
            name='MasterValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField()),
                ('master_field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.masterfield')),
            ],
        ),
        migrations.CreateModel(
            name='MasterEntity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.source')),
                ('source_entity', models.ManyToManyField(to='masterdata.SourceEntity')),
            ],
        ),
        migrations.CreateModel(
            name='MasterData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('master_entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.masterentity')),
                ('master_field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.masterfield')),
                ('master_value', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masterdata.mastervalue')),
                ('source_data', models.ManyToManyField(to='masterdata.SourceData')),
            ],
        ),
    ]
