from django import forms
from django.core.exceptions import ValidationError
from .models import Scan


def validate_file_extension(file):
    if not file.name.endswith('.json'):
        raise ValidationError(
            u'Wrong file type. The file needs to be in json format.')


class ScanDataImportForm(forms.Form):
    file = forms.FileField(label="Upload .json file",
                           validators=[validate_file_extension])


class ScanEditForm(forms.ModelForm):
    STATUS_CHOICES = [
        ("Waiting for upload", "Waiting for upload"),
        ("IN_PROGRESS", "In progress"),
        ("JPG DONE", "JPG done"),
        ("FINISHED", "Quality Check finished")
    ]
    TYPE_CHOICES = [
        ("Accession card", "Accession card"),
        ("Accession card, printout I", "Accession card, printout"),
        ("Accession card, handwritten", "Accession card, handwritten"),
        ("Accession card, small", "Accession card, small"),
        ("Accession card, big", "Accession card, big"),
        ("Comment Slip", "Comment slip"),
        ("Other slips II", "Other slips"),
        ("Other", "Other"),
        ("Unclear", "Unclear"),
    ]

    status = forms.ChoiceField(choices=STATUS_CHOICES)
    type = forms.ChoiceField(choices=TYPE_CHOICES)

    class Meta:
        model = Scan
        fields = ['type', 'status', 'text']
