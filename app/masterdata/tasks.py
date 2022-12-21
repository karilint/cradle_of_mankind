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
    get_queryset_dict,
    get_master_source_data_ids,
    create_source_fields,
    set_primary_keys,
    get_source_key,
    get_master_key_for_source_entity,
    get_master_value,
    stage4_post,
)
from .models import (
    Source,
    SourceField,
    SourceEntity,
    SourceData,
    MasterEntity,
    MasterField,
    MasterData,
    MasterSourceData,
    Value,
)


logger = get_task_logger(__name__)


@shared_task(bind=True)
def import_source_data(self, source_import, request_post):
    source_file_path = source_import.pop("source_file_path")
    source = Source(**source_import)
    source.source_file.name = source_file_path
    source_fields = create_source_fields(source)
    set_primary_keys(request_post, source_fields)
    logger.info(f"Starting source data import")
    set_task_state(self, "PROGRESS")
    logger.info(f"Determining IDs for the source and sourcefields")
    record_progress(
        self, 0, 1, 1, "Determining IDs for the source and sourcefields"
    )
    last_source = Source.objects.order_by("id").last()
    last_source_field = SourceField.objects.order_by("id").last()
    last_source_entity = SourceEntity.objects.order_by("id").last()
    last_source_data = SourceData.objects.order_by("id").last()
    last_value = Value.objects.order_by("id").last()
    source.id = last_source.id + 1 if last_source else 1
    last_source_field_id = last_source_field.id if last_source_field else 0
    last_source_entity_id = last_source_entity.id if last_source_entity else 0
    last_source_data_id = last_source_data.id if last_source_data else 0
    last_value_id = last_value.id if last_value else 0
    for idx, source_field in enumerate(source_fields, 1):
        source_field.id = last_source_field_id + idx
    source_entity_objs = []
    source_data_objs = []
    new_value_objs = []
    with open(source.source_file.path, encoding="utf8") as f:
        source_data = csv.DictReader(f, delimiter=source.delimiter)
        total_work = len(list(source_data))
        source_field_dict = {}
        for field in source_fields:
            source_field_dict[field.name] = field
        values_dict = {}
        for idx, value in Value.objects.values_list("id", "value"):
            values_dict[value] = idx
        f.seek(0)
        source_data = csv.DictReader(f, delimiter=source.delimiter)
        for idx, row in enumerate(source_data, 1):
            record_progress(
                self, idx, total_work, 500, "Processing source data..."
            )
            # Source Entities
            source_entity = SourceEntity()
            source_entity.id = last_source_entity_id + idx
            source_entity.source_key = get_source_key(source_fields, row)
            source_entity.source_id = source.id
            source_entity_objs.append(source_entity)
            for col_idx, field in enumerate(row.keys(), 1):
                # New Values
                row_col_value = row[field].strip()
                if not row_col_value in values_dict:
                    new_value = Value()
                    last_value_id += 1
                    new_value.id = last_value_id
                    new_value.value = row_col_value
                    new_value_objs.append(new_value)
                    values_dict[row_col_value] = last_value_id
                # Source Datas
                source_data = SourceData()
                source_data.id = (
                    last_source_data_id + col_idx + len(row.keys()) * (idx - 1)
                )
                source_data.source_entity_id = source_entity.id
                source_data.source_field_id = source_field_dict[field].id
                source_data.value_id = values_dict[row_col_value]
                source_data_objs.append(source_data)
    logger.info("Saving source data to database...")
    record_progress(
        self,
        total_work,
        total_work,
        1,
        "Saving source data to database... This might take awhile",
    )
    # DATABASE TRANSACTION
    with transaction.atomic():
        Value.objects.bulk_create(new_value_objs, batch_size=5000)
        source.save()
        SourceField.objects.bulk_create(source_fields, batch_size=5000)
        SourceEntity.objects.bulk_create(source_entity_objs, batch_size=5000)
        SourceData.objects.bulk_create(source_data_objs, batch_size=5000)


@shared_task(bind=True)
def create_master_data(self, source_id):
    logger.info(f"Starting masterdata creation for source ({source_id})")
    set_task_state(self, "PROGRESS")

    source = Source.objects.get(id=source_id)
    source_datas = SourceData.objects.select_related("value").filter(
        source_entity__source=source
    )
    source_fields = SourceField.objects.filter(source=source)
    master_rules = json.loads(source.masterdata_rules)
    master_fields = MasterField.objects.all()
    total_work = source.source_entities.count()

    # Already existing objs
    source_data_dict = get_queryset_dict(
        source_datas, "source_entity_id", "source_field_id"
    )
    source_field_dict = get_queryset_dict(source_fields)
    entity_dict = get_queryset_dict(MasterEntity.objects.all(), "master_key")
    value_dict = get_queryset_dict(Value.objects.all(), "value")

    # Last id/pk
    last_master_entity = MasterEntity.objects.order_by("id").last()
    last_master_data = MasterData.objects.order_by("id").last()
    last_value = Value.objects.order_by("id").last()
    last_me_id = last_master_entity.id if last_master_entity else 0
    last_md_id = last_master_data.id if last_master_data else 0
    last_value_id = last_value.id if last_value else 0

    new_value_objs = []
    new_master_entity_objs = []
    new_master_data_objs = []
    new_master_source_data_objs = []

    for counter, source_entity in enumerate(source.source_entities.all(), 1):
        logger.debug(f"Masterdata progress: {counter} of {total_work}")
        record_progress(
            self,
            counter,
            total_work,
            100,
            "Creating master data from the source...",
        )
        master_key = get_master_key_for_source_entity(
            source_entity, master_rules
        )
        # MasterEntity
        if master_key in entity_dict:
            master_entity = entity_dict[master_key]
        else:
            last_me_id += 1
            master_entity = MasterEntity()
            master_entity.id = last_me_id
            master_entity.master_key = master_key
            new_master_entity_objs.append(master_entity)
            entity_dict[master_key] = master_entity

        # MasterData + Values
        for master_field in master_fields:
            master_value = get_master_value(
                source,
                source_entity,
                master_field,
                source_field_dict,
                source_data_dict,
            )
            source_data_ids = get_master_source_data_ids(
                source,
                source_entity,
                master_field,
                source_field_dict,
                source_data_dict,
            )
            if not master_value in value_dict:
                last_value_id += 1
                new_value = Value()
                new_value.id = last_value_id
                new_value.value = master_value
                new_value_objs.append(new_value)
                value_dict[master_value] = new_value
            last_md_id += 1
            master_data = MasterData()
            master_data.id = last_md_id
            master_data.value = value_dict[master_value]
            master_data.master_entity = master_entity
            master_data.master_field = master_field
            new_master_data_objs.append(master_data)
            for source_data_id in source_data_ids:
                msd = MasterSourceData()
                msd.source_data_id = source_data_id
                msd.master_data_id = master_data.id
                new_master_source_data_objs.append(msd)

    logger.info("Saving master data to database...")
    record_progress(
        self,
        total_work,
        total_work,
        1,
        "Saving master data to database... This might take awhile",
    )
    with transaction.atomic():
        logger.info(
            f"Saving values to database "
            f"(object count {len(new_value_objs)})"
        )
        Value.objects.bulk_create(new_value_objs, batch_size=5000)
        logger.info(
            f"Saving master_entities to database "
            f"(object count {len(new_master_entity_objs)})"
        )
        MasterEntity.objects.bulk_create(
            new_master_entity_objs, batch_size=5000
        )
        logger.info(
            f"Saving master_datas to database "
            f"(object count {len(new_master_data_objs)})"
        )
        MasterData.objects.bulk_create(new_master_data_objs, batch_size=5000)
        logger.info(
            f"Saving master_data and source_data "
            f"connections to database (object count "
            f"{len(new_master_source_data_objs)})"
        )
        MasterSourceData.objects.bulk_create(
            new_master_source_data_objs, batch_size=5000
        )
        source.master_created = True
        source.save()


@shared_task(bind=True)
def edit_master_data(self, source_id):
    logger.info(f"Starting masterdata creation for source ({source_id})")
    set_task_state(self, "PROGRESS")

    source = Source.objects.get(id=source_id)
    source_datas = SourceData.objects.select_related("value").filter(
        source_entity__source=source
    )
    source_fields = SourceField.objects.filter(source=source)
    master_rules = json.loads(source.masterdata_rules)
    master_fields = MasterField.objects.exclude(
        master_datas__source_datas__source_entity__source=source
    )
    total_work = source.source_entities.count()

    # Already existing objs
    source_data_dict = get_queryset_dict(
        source_datas, "source_entity_id", "source_field_id"
    )
    source_field_dict = get_queryset_dict(source_fields)
    entity_dict = get_queryset_dict(MasterEntity.objects.all(), "master_key")
    value_dict = get_queryset_dict(Value.objects.all(), "value")

    # Last id/pk
    last_master_data = MasterData.objects.order_by("id").last()
    last_value = Value.objects.order_by("id").last()
    last_md_id = last_master_data.id if last_master_data else 0
    last_value_id = last_value.id if last_value else 0

    new_value_objs = []
    new_master_data_objs = []
    new_master_source_data_objs = []

    for counter, source_entity in enumerate(source.source_entities.all(), 1):
        logger.debug(f"Masterdata progress: {counter} of {total_work}")
        record_progress(
            self,
            counter,
            total_work,
            100,
            "Creating master data from the source...",
        )
        master_key = get_master_key_for_source_entity(
            source_entity, master_rules
        )
        master_entity = entity_dict[master_key]
        for master_field in master_fields:
            master_value = get_master_value(
                source,
                source_entity,
                master_field,
                source_field_dict,
                source_data_dict,
            )
            source_data_ids = get_master_source_data_ids(
                source,
                source_entity,
                master_field,
                source_field_dict,
                source_data_dict,
            )
            if not master_value in value_dict:
                last_value_id += 1
                new_value = Value()
                new_value.id = last_value_id
                new_value.value = master_value
                new_value_objs.append(new_value)
                value_dict[master_value] = new_value
            last_md_id += 1
            master_data = MasterData()
            master_data.id = last_md_id
            master_data.value = value_dict[master_value]
            master_data.master_entity = master_entity
            master_data.master_field = master_field
            new_master_data_objs.append(master_data)
            for source_data_id in source_data_ids:
                msd = MasterSourceData()
                msd.source_data_id = source_data_id
                msd.master_data_id = master_data.id
                new_master_source_data_objs.append(msd)
    logger.info("Saving master data to database...")
    record_progress(
        self,
        total_work,
        total_work,
        1,
        "Saving master data to database... This might take awhile",
    )
    with transaction.atomic():
        logger.info(
            f"Saving values to database "
            f"(object count {len(new_value_objs)})"
        )
        Value.objects.bulk_create(new_value_objs, batch_size=5000)
        logger.info(
            f"Saving master_datas to database "
            f"(object count {len(new_master_data_objs)})"
        )
        MasterData.objects.bulk_create(new_master_data_objs, batch_size=5000)
        logger.info(
            f"Saving master_data and source_data "
            f"connections to database (object count "
            f"{len(new_master_source_data_objs)})"
        )
        MasterSourceData.objects.bulk_create(
            new_master_source_data_objs, batch_size=5000
        )


@shared_task(bind=True)
def delete_master(self, source_id):
    logger.info(f"Starting masterdata deletion for source ({source_id})")
    set_task_state(self, "PROGRESS")
    source = Source.objects.get(pk=source_id)
    record_progress(self, 0, 1, 1, "Deleting objects... This takes a while")
    with transaction.atomic():
        (
            MasterData.objects.filter(
                source_datas__source_entity__source_id=source_id
            ).delete()
        )
        (
            Value.objects.filter(master_datas__isnull=True)
            .filter(source_datas__isnull=True)
            .filter(prev_value_comments__isnull=True)
            .filter(new_value_comments__isnull=True)
            .delete()
        )
        (
            MasterSourceData.objects.filter(
                source_data__source_entity__source_id=source_id
            ).delete()
        )
        MasterEntity.objects.filter(master_datas__isnull=True).delete()
        source.master_created = False
        source.masterdata_stage = 0
        source.masterdata_rules = None
        source.save()
