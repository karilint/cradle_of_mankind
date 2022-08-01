import os

from django.conf import settings


def check_imported_files():
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
    return all_files_exist

