"""Upload form shared by every entity importer."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .base import MAX_IMPORT_FILE_SIZE


class EntityImportForm(forms.Form):
    file = forms.FileField(
        label=_("CSV file"),
        help_text=_("UTF-8 encoded .csv file (max 10 MB)."),
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": ".csv"}
        ),
    )

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
        if ext != "csv":
            raise forms.ValidationError(
                _("Unsupported format. Please provide a .csv file.")
            )
        if uploaded.size > MAX_IMPORT_FILE_SIZE:
            raise forms.ValidationError(
                _("The file exceeds the maximum allowed size (10 MB).")
            )
        return uploaded
