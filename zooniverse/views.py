from json.decoder import JSONDecodeError
import os
from json import loads
from csv import DictReader
from datetime import datetime
from quality_control.models import AnnotationField
from users.views import user_is_data_admin

from django.contrib import messages
from scans.models import Scan
from pytz import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import DataImportForm
from .models import Retirement, Workflow, Classification, Annotation, Subject


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
            messages.warning(request, "Update couldn't start. Have you uploaded all the required files? (specimen-numbers-classifications.csv, location-and-stratigraphy-classifications.csv, additional-info-card-backside-classifications.csv, specimen-taxonomy-latin-names-classifications.csv, nature-of-specimen-body-parts-classifications.csv)")
        redirect('index')
    form = DataImportForm()
    return render(request, 'zooniverse/zooniverse_import.html', {'form': form})


def update_database():
    required_files = [
        'specimen-numbers-classifications.csv',
        'location-and-stratigraphy-classifications.csv',
        'additional-info-card-backside-classifications.csv',
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

    existing_workflow_ids = set(
        Workflow.objects.all().values_list('id', flat=True))
    existing_subject_ids = set(
        Subject.objects.all().values_list('id', flat=True))
    existing_retirement_ids = set(
        Retirement.objects.all().values_list('id', flat=True))
    existing_classification_ids = set(
        Classification.objects.all().values_list('id', flat=True))
    classifications_without_retirement = set(
        Classification.objects.filter(retirement=None).values_list('id', flat=True))
    existing_annotations = set(map(lambda x: '|'.join(
        map(str, x)), Annotation.objects.all().values_list('classification_id', 'task')))
    new_workflows = []
    new_subjects = []
    new_retirements = []
    new_classifications = []
    classifications_to_be_updated = []
    new_annotations = []
    for file in required_files:
        with open(os.path.join(imports_path, file), encoding='utf8') as f:
            data = DictReader(f)
            rows = 0
            for row in data:
                rows += 1
            f.seek(0)
            data = DictReader(f)
            print(f"Processing... {file} ({rows} rows)")
            for index, row in enumerate(data, 1):
                div = rows//5
                if (index) % div == 0:
                    print(f"Processing... {file} ({(2*index)//div}0% done)")

                eet = timezone('Europe/Helsinki')
                created_at = eet.localize(datetime.strptime(
                    row['created_at'], '%Y-%m-%d %H:%M:%S %Z'))
                if created_at < eet.localize(datetime(2020, 8, 17, 14, 50, 17)):
                    continue

                save_workflow(row, existing_workflow_ids, new_workflows)
                subject_id = save_subject(
                    row, index, existing_subject_ids, new_subjects)
                retirement_id = save_retirement(
                    row, index, eet, existing_retirement_ids, new_retirements)
                classification_id = save_classification(
                    row, eet, existing_classification_ids, new_classifications,
                    classifications_without_retirement, classifications_to_be_updated,
                    retirement_id, subject_id)
                save_annotations(
                    row, index, existing_annotations, new_annotations, classification_id)
    print("Saving workflows to database...")
    Workflow.objects.bulk_create(new_workflows, batch_size=5000)
    print("Saving subjects to database...")
    Subject.objects.bulk_create(new_subjects, batch_size=5000)
    print('Saving retirements to database...')
    Retirement.objects.bulk_create(new_retirements, batch_size=5000)
    print('Saving classifications to database...')
    Classification.objects.bulk_create(new_classifications, batch_size=5000)
    Classification.objects.bulk_update(classifications_to_be_updated, [
                                       'retirement'], batch_size=5000)
    print('Saving annotations to database...')
    Annotation.objects.bulk_create(new_annotations, batch_size=5000)
    update_annotation_fields()
    return True


def save_annotations(row, index, existing_annotations, new_annotations, classification_id):
    try:
        annotations_data = loads(row['annotations'])
        for annotation in annotations_data:
            annotation_combined_id = '|'.join(
                (str(classification_id), annotation['task']))
            if annotation_combined_id not in existing_annotations:
                new_annotation = Annotation()
                new_annotation.classification_id = classification_id
                new_annotation.task = annotation['task']
                new_annotation.task_label = annotation['task_label']
                if annotation['value'] is not None:
                    new_annotation.value = annotation['value']
                new_annotations.append(new_annotation)
                existing_annotations.add(annotation_combined_id)
    except (JSONDecodeError, KeyError) as e:
        print(f"ERROR WHEN PARSING SUBJECT DATA (ROW {index})")
        print(row)
        print(e)


def save_classification(row, eet, existing_classification_ids,
                        new_classifications, classifications_without_retirement,
                        classifications_to_be_updated, retirement_id, subject_id):
    classification_id = int(row['classification_id'])
    if classification_id not in existing_classification_ids:
        new_classification = Classification()
        new_classification.id = classification_id
        new_classification.user_name = row['user_name']
        new_classification.user_id = row['user_id']
        new_classification.user_ip = row['user_ip']
        new_classification.workflow_version = row['workflow_version']
        new_classification.created_at = eet.localize(datetime.strptime(
            row['created_at'], '%Y-%m-%d %H:%M:%S %Z'))
        new_classification.gold_standard = row['gold_standard']
        new_classification.expert = row['expert']
        new_classification.meta_data = row['metadata']
        new_classification.subject_id = subject_id
        if retirement_id:
            new_classification.retirement_id = retirement_id
        new_classification.workflow_id = row['workflow_id']
        new_classifications.append(new_classification)
        existing_classification_ids.add(classification_id)
    elif classification_id in classifications_without_retirement and retirement_id:
        classifications_without_retirement.add(classification_id)
        classification = Classification.objects.get(id=classification_id)
        classification.retirement_id = retirement_id
        classifications_to_be_updated.append(classification)
    return classification_id


def save_retirement(row, index, eet, existing_retirement_ids, new_retirements):
    try:
        subject_data = loads(row['subject_data'])
        for _, subject_row in subject_data.items():
            if subject_row['retired']:
                retirement = subject_row['retired']
                retirement_id = int(retirement['id'])
                if retirement_id not in existing_retirement_ids:
                    new_retirement = Retirement()
                    new_retirement.id = retirement['id']
                    new_retirement.classifications_count = retirement['classifications_count']
                    new_retirement.created_at = eet.localize(datetime.strptime(
                        retirement['created_at'][:19], '%Y-%m-%dT%H:%M:%S'))
                    new_retirement.updated_at = eet.localize(datetime.strptime(
                        retirement['updated_at'][:19], '%Y-%m-%dT%H:%M:%S'))
                    new_retirement.retired_at = eet.localize(datetime.strptime(
                        retirement['retired_at'][:19], '%Y-%m-%dT%H:%M:%S'))
                    new_retirement.retirement_reason = retirement['retirement_reason']
                    new_retirement.subject_id = retirement['subject_id']
                    new_retirement.workflow_id = retirement['workflow_id']
                    new_retirements.append(new_retirement)
                    existing_retirement_ids.add(new_retirement.id)
                return retirement_id
    except JSONDecodeError as e:
        print(f"ERROR WHEN PARSING SUBJECT DATA (ROW {index})")
        print(row)
        print(e)


def save_subject(row, index, existing_subject_ids, new_subjects):
    try:
        subject_data = loads(row['subject_data'])
        for subject_id, subject in subject_data.items():
            subject_id = int(subject_id)
            if subject_id not in existing_subject_ids:
                new_subject = Subject()
                new_subject.id = subject_id
                new_subject.scan_id = get_scan_id(
                    subject['Filename'])
                new_subjects.append(new_subject)
                existing_subject_ids.add(subject_id)
            return subject_id
    except (JSONDecodeError, KeyError) as e:
        print(f"ERROR WHEN PARSING SUBJECT DATA (ROW {index})")
        print(row)
        print(e)


def get_scan_id(scan_filename):
    first_digit_idx = -1
    for i in range(len(scan_filename)):
        if scan_filename[i].isdigit():
            first_digit_idx = i
            break
    return int(scan_filename[first_digit_idx:scan_filename.find('.')])


def save_workflow(row, existing_workflow_ids, new_workflows):
    workflow_id = int(row['workflow_id'])
    workflow_name = row['workflow_name']
    if workflow_id not in existing_workflow_ids:
        new_workflow = Workflow()
        new_workflow.id = workflow_id
        new_workflow.name = workflow_name
        new_workflows.append(new_workflow)
        existing_workflow_ids.add(workflow_id)
    return workflow_id


def update_annotation_fields():
    fields = ['Locality', 'SITE/AREA', 'Formation', 'Mbr/Horizon/Etc.',
              'Photo', 'Coordinates', 'Pfx', 'AN', 'FN', 'FN (Pre)',
              'Shelf', 'Date', 'Published', 'Type', 'PTO', 'Body parts',
              'Fragments', 'Taxon', 'Family', 'Subfamily', 'Tribe', 'Genus',
              'Species', 'Reference', 'Coordinates', 'Photo', 'Other']
    for name in fields:
        try:
            AnnotationField.objects.get(name=name)
        except AnnotationField.DoesNotExist:
            field = AnnotationField()
            field.name = name
            field.save()
