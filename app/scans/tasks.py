from django.db import transaction

from celery import shared_task
from celery.utils.log import get_task_logger

from .models import Scan
from users.models import User
from tasks.utils import record_progress, set_task_state


logger = get_task_logger(__name__)


@shared_task(bind=True)
def save_scan_data(self, scan_data, user_id):
    logger.info(f"Starting scan data import")
    set_task_state(self, 'PROGRESS')
    user = User.objects.get(id=user_id)
    existing_ids = set(Scan.objects.all().values_list('id', flat=True))
    total_work = len(scan_data['rows'])
    record_progress(self, 0, total_work)
    logger.info(f"Going through scan data")
    new_scans = []
    for current_work, obj in enumerate(scan_data['rows'], 1):
        if obj['id'] in existing_ids:
            record_progress(self, current_work, total_work, 100)
            continue
        else:
            scan = Scan()
            scan.id = obj['id']
            scan.type = obj['card_type']
            scan.status = obj['STG_STATUS']
            scan.image = f"scans/{scan.id}.jpg"
            if not obj['txt']:
                scan.text = ''
            else:
                scan.text = obj['txt']
            scan.created_by = user
            scan.modified_by = user
            new_scans.append(scan)
            logger.debug(f"New scan (id: {scan.id}) created")
            record_progress(self, current_work, total_work, 100)
    logger.info(f"Total of {len(new_scans)} new scans created")
    logger.info(f"Saving scan objects to database")
    record_progress(self, total_work, total_work, 1, "Saving scans to database...")
    with transaction.atomic():
        Scan.objects.bulk_create(new_scans)

