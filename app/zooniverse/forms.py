from django import forms
from .models import Import


class ImportForm(forms.ModelForm):
    """A partial form for the Zooniverse Import

    Note: 'created_by' needs to be given in the view
    """

    class Meta:
        model = Import
        fields = ["file"]
        labels = {
            "file": "Upload CSV file",
        }
