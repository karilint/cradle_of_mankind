import os
import csv
import json

from datetime import datetime
from pytz import timezone
from json.decoder import JSONDecodeError

from celery import shared_task
from celery.utils.log import get_task_logger
from celery_progress.backend import ProgressRecorder
from django_celery_results.models import TaskResult
from django.conf import settings
from django.db import transaction

from tasks.utils import record_progress, set_task_state
from quality_control.models import AnnotationField

from .utils import (
    create_source_fields, 
    set_primary_keys,
    get_source_key,
    get_master_key_for_source_entity,
    stage4_post,
)
from .models import (
    Source, 
    SourceField, 
    SourceEntity, 
    SourceData, 
    SourceValue,
    MasterEntity,
    MasterField,
    MasterData,
    MasterValue,
)


logger = get_task_logger(__name__)


@shared_task(bind=True)
def import_source_data(self, source_import, request_post):
    source_file_path = source_import.pop('source_file_path')
    source = Source(**source_import)
    source.source_file.name = source_file_path
    source_fields = create_source_fields(source)
    set_primary_keys(request_post, source_fields)
    logger.info(f"Starting source data import")
    set_task_state(self, 'PROGRESS')
    logger.info(f"Determining IDs for the source and sourcefields")
    record_progress(self, 0, 1, 1, "Determining IDs for the source and sourcefields")
    source.id = Source.objects.last().id + 1
    last_source_field_id = SourceField.objects.order_by('id').last().id
    last_source_entity_id = SourceEntity.objects.order_by('id').last().id
    last_source_data_id = SourceData.objects.order_by('id').last().id
    last_source_value_id = SourceValue.objects.order_by('id').last().id
    for idx, source_field in enumerate(source_fields, 1):
        source_field.id = last_source_field_id + idx
    source_entity_objs = []
    source_data_objs = []
    source_value_objs = []
    with open(source.source_file.path, encoding='utf8') as f:
        source_data = csv.DictReader(f, delimiter=source.delimiter)
        total_work = len(list(source_data))
        source_field_dict = {}
        for field in source_fields:
            source_field_dict[field.name] = field
        f.seek(0)
        source_data = csv.DictReader(f, delimiter=source.delimiter)
        for idx, row in enumerate(source_data, 1):
            record_progress(self, idx, total_work, 500, "Processing source data...")
            # Source Entities
            source_entity = SourceEntity()
            source_entity.id = last_source_entity_id + idx
            source_entity.source_key = get_source_key(source_fields, row)
            source_entity.source_id = source.id
            source_entity_objs.append(source_entity)
            for col_idx, field in enumerate(row.keys(), 1):
                # Source Datas
                source_data = SourceData()
                source_data.id = last_source_data_id + col_idx + len(row.keys())*(idx - 1)
                source_data.source_entity_id = source_entity.id
                source_data.source_field_id = source_field_dict[field].id
                source_data_objs.append(source_data)
                # Source Values
                source_value = SourceValue()
                source_value.id = last_source_value_id + col_idx + len(row.keys())*(idx -1)
                source_value.value = row[field].strip()
                source_value.source_field_id = source_field_dict[field].id
                source_value.source_data_id = source_data.id
                source_value_objs.append(source_value)
    logger.info("Saving source data to database...")
    record_progress(self, total_work, total_work, 1, "Saving source data to database... This might take awhile")
    # DATABASE TRANSACTION
    with transaction.atomic():
        source.save()
        SourceField.objects.bulk_create(source_fields)
        SourceEntity.objects.bulk_create(source_entity_objs, batch_size=5000)
        SourceData.objects.bulk_create(source_data_objs, batch_size=5000)
        SourceValue.objects.bulk_create(source_value_objs, batch_size=5000)


@shared_task(bind=True)
def create_master_data(self, source_id):
    logger.info(f"Starting masterdata creation")
    set_task_state(self, 'PROGRESS')
    record_progress(self, 1, 100, 1, "Live progress is not recorded for this process. This might take awhile.")
    with transaction.atomic():
        source = Source.objects.get(id=source_id)
        master_rules = json.loads(source.masterdata_rules)
        master_fields = MasterField.objects.all()
        total_work = source.sourceentity_set.count()
        for counter, source_entity in enumerate(source.sourceentity_set.all(), 1):
            logger.debug(f"Masterdata progress: {counter} of {total_work}")
            master_key = get_master_key_for_source_entity(
                source_entity, master_rules)
            try:
                master_entity = MasterEntity.objects.get(
                    master_key=master_key)
                master_entity.source_entities.add(source_entity)
                for master_field in MasterField.objects.all():
                    source_datas = []
                    master_field_rules = master_rules[str(master_field.id)]
                    if not master_field_rules:
                        continue
                    ordered_keys = sorted(list(master_field_rules.keys()))
                    master_value = MasterValue()
                    master_data = MasterData.objects.get(
                        master_entity=master_entity, master_field=master_field)
                    master_value.master_field = master_field
                    master_value.value = ''
                    for key in ordered_keys:
                        source_field = SourceField.objects.get(
                            pk=master_field_rules[key]['source_field'])
                        source_data = SourceData.objects.get(
                            source_entity=source_entity, source_field=source_field)
                        if source_field.is_divided:
                            part = master_field_rules[key]['part']
                            try:
                                value = re.split(
                                    source_field.delimiters, source_data.source_value.value)[part-1]
                            except IndexError:
                                logger.warning(
                                    f'Splitting not possible. Tried to get part {part} of "{source_data.source_value.value}". Using Empty string.')
                                value = ''
                            master_value.value += value
                            master_value.value += master_field_rules[key]['ending']
                        else:
                            master_value.value += source_data.source_value.value
                            master_value.value += master_field_rules[key]['ending']
                        source_datas.append(source_data)
                    master_value.master_data = master_data
                    master_value.save()
                    master_data.save()
                    for data in source_datas:
                        master_data.source_data.add(data)
                        master_value.source_data.add(data)
                    master_field.save()

            except MasterEntity.DoesNotExist:
                master_entity = MasterEntity()
                master_entity.master_key = master_key
                master_entity.source = source
                master_entity.save()
                master_entity.source_entities.add(source_entity)
                stage4_post(source, source_entity, master_entity,
                            master_fields, master_rules)
        source.master_created = True
        source.save()


