from django import forms
from .models import MasterField


class SourceDataImportForm(forms.Form):
    source_name = forms.CharField(max_length=255)
    file = forms.FileField(label="Upload a CSV file containing source data")
    delimiter = forms.CharField(max_length=255, label='CSV delimiter')


class MasterFieldForm(forms.ModelForm):

    class Meta:
        model = MasterField
        fields = ['name', 'description']
