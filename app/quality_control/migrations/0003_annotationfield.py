# Generated by Django 3.1.2 on 2021-01-07 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quality_control', '0002_auto_20201221_2221'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnotationField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
    ]