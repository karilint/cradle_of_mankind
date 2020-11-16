from django import forms


class DataImportForm(forms.Form):
    file = forms.FileField(label="Upload a CSV file from Zooniverse")
