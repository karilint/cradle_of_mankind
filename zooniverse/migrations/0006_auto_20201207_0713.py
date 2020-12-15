# Generated by Django 3.1.2 on 2020-12-07 05:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('zooniverse', '0005_auto_20201203_1237'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subject',
            name='retirement',
        ),
        migrations.AddField(
            model_name='retirement',
            name='checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='retirement',
            name='subject',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='zooniverse.subject'),
        ),
    ]
