from django import forms


class SourceDataImportForm(forms.Form):
    source_name = forms.CharField(max_length=255)
    file = forms.FileField(label="Upload a CSV file containing source data")
    delimiter = forms.CharField(max_length=255, label='CSV delimiter')


class MasterFieldForm(forms.Form):
    field_name = forms.CharField(max_length=255)
    field_description = forms.CharField(max_length=1000, required=False)
