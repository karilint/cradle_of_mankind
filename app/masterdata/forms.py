from django import forms
from .models import MasterField, Source


class SourceDataImportForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = [
            "name",
            "description",
            "reference",
            "source_file",
            "delimiter",
        ]
        labels = {
            "name": "Source name",
            "description": "Description",
            "reference": "Reference",
            "source_file": "Upload a CSV file containing source data",
            "delimiter": "CSV delimiter",
        }


class MasterFieldForm(forms.ModelForm):
    class Meta:
        model = MasterField
        fields = [
            "name",
            "abbreviation",
            "access_level",
            "description",
            "primary_key",
            "hidden",
        ]


class MasterFieldOrderingForm(forms.Form):
    ordering = forms.CharField()
