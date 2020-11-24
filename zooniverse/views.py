from json.decoder import JSONDecodeError
import os
from json import loads
from csv import DictReader
from datetime import datetime

from django.contrib import messages
from scans.models import Scan
from pytz import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import DataImportForm
from .models import Workflow, Classification, Annotation, Subject


def user_is_data_admin(user):
    return user.is_data_admin


def save_uploaded_file(f):
    try:
        os.mkdir(os.path.join(settings.MEDIA_ROOT, 'imports'))
    except:
        pass

    path_to_file = os.path.join(settings.MEDIA_ROOT, 'imports', f.name)
    with open(path_to_file, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


@login_required
@user_passes_test(user_is_data_admin)
def import_data(request):
    if request.method == 'POST' and 'btn-upload' in request.POST:
        form = DataImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            save_uploaded_file(f)
    elif request.method == 'POST' and 'btn-update-db' in request.POST:
        success = update_database()
        if success:
            messages.success(request, "Update was succesful!")
        else:
            messages.warning(request, "Update couldn't start. Have you uploaded all the required files? (specimen-numbers-classifications.csv, location-and-stratigraphy-classifications.csv, additional-info-classifications.csv, specimen-taxonomy-latin-names-classifications.csv, nature-of-specimen-body-parts-classifications.csv)")
        redirect('index')
    form = DataImportForm()
    return render(request, 'zooniverse/zooniverse_import.html', {'form': form})


def update_database():
    required_files = [
        'specimen-numbers-classifications.csv',
        'location-and-stratigraphy-classifications.csv',
        'additional-info-classifications.csv',
        'specimen-taxonomy-latin-names-classifications.csv',
        'nature-of-specimen-body-parts-classifications.csv'
    ]

    imports_path = os.path.join(settings.MEDIA_ROOT, 'imports')
    files = [f for f in os.listdir(imports_path) if os.path.isfile(
        os.path.join(imports_path, f))]
    all_files_exist = True
    for file in required_files:
        if file not in files:
            all_files_exist = False
    if not all_files_exist:
        return False

    for file in required_files:
        with open(os.path.join(imports_path, file)) as f:
            data = DictReader(f)
            print(f"Processing... {file}")
            for index, row in enumerate(data):
                try:
                    classification = Classification.objects.get(
                        id=row['classification_id'])
                except ObjectDoesNotExist:
                    classification = Classification()
                    classification.id = row['classification_id']
                classification.user_name = row['user_name']
                classification.user_id = row['user_id']
                classification.user_ip = row['user_ip']
                classification.workflow_version = row['workflow_version']
                eet = timezone('Europe/Helsinki')
                classification.created_at = eet.localize(datetime.strptime(
                    row['created_at'], '%Y-%m-%d %H:%M:%S %Z'))
                if classification.created_at < eet.localize(datetime(2020, 8, 17, 14, 50, 17)):
                    continue
                classification.gold_standard = row['gold_standard']
                classification.expert = row['expert']
                classification.meta_data = row['metadata']

                try:
                    workflow = Workflow.objects.get(id=row['workflow_id'])
                except Workflow.DoesNotExist:
                    workflow = Workflow()
                    workflow.id = row['workflow_id']
                    workflow.name = row['workflow_name']
                    workflow.save()
                classification.workflow = workflow
                classification.save()

                try:
                    annotations_data = loads(row['annotations'])
                    for annotation in annotations_data:
                        try:
                            a = Annotation.objects.get(
                                task=annotation['task'], classification=classification)
                        except Annotation.DoesNotExist:
                            a = Annotation()
                            a.classification = classification
                            a.task = annotation['task']
                        a.task_label = annotation['task_label']
                        a.value = annotation['value']
                        a.save()
                except (JSONDecodeError, KeyError) as e:
                    print(f"ERROR WHEN PARSING ANNOTATIONS (ROW {index})")
                    print(index)
                    print(e)

                try:
                    subject_data = loads(row['subject_data'])
                    for subject_id, subject in subject_data.items():
                        try:
                            s = Subject.objects.get(id=subject_id)
                        except Subject.DoesNotExist:
                            s = Subject()
                            s.id = subject_id
                        if subject['retired']:
                            s.workflow = Workflow.objects.get(
                                id=subject['retired']['workflow_id'])
                            s.classification = classification
                            s.classifications_count = subject['retired']['classifications_count']
                            s.created_at = eet.localize(datetime.strptime(
                                subject['retired']['created_at'][:19], '%Y-%m-%dT%H:%M:%S'))
                            s.updated_at = eet.localize(datetime.strptime(
                                subject['retired']['updated_at'][:19], '%Y-%m-%dT%H:%M:%S'))
                            s.retired_at = eet.localize(datetime.strptime(
                                subject['retired']['retired_at'][:19], '%Y-%m-%dT%H:%M:%S'))
                            s.retirement_reason = subject['retired']['retirement_reason']

                        scan_filename = subject['Filename']
                        first_digit_idx = -1
                        for i in range(len(scan_filename)):
                            if scan_filename[i].isdigit():
                                first_digit_idx = i
                                break
                        scan_id = int(
                            scan_filename[first_digit_idx:scan_filename.find('.')])
                        s.scan = Scan.objects.get(id=scan_id)
                        s.save()
                except (JSONDecodeError, KeyError) as e:
                    print(f"ERROR WHEN PARSING SUBJECT DATA (ROW {index})")
                    print(e)
    return True
