from django import forms
from django.utils.translation import gettext as _
from tools.forms.settings import BLANK_CHOICE

OOI_TYPE_CHOICES = [
    BLANK_CHOICE,
    ("URL", "URL"),
    ("Hostname", "Hostname"),
    ("IPAddressV4", "IPAddressV4"),
    ("IPAddressV6", "IPAddressV6"),
]

CSV_ERRORS = {
    "only_csv": _("Only CSV file supported"),
    "decoding": _("File could not be decoded"),
    "no_file": _("No file selected"),
    "empty_file": _("The uploaded file is empty."),
    "no_org": _("Organization code(s) in CSV does not exist in our database"),
    "bad_columns": _("The number of columns does not meet the requirements."),
    "bad_ooi_type": _("OOI Type in CSV does not meet the criterias."),
    "csv_error": _("An error has occurred during the parsing of the csv file:"),
}


class UploadCSVForm(forms.Form):
    object_type = forms.ChoiceField(
        label=_("Object Type"),
        choices=OOI_TYPE_CHOICES,
        help_text=_("Choose a type of which objects are added."),
        required=True,
    )
    csv_file = forms.FileField(
        label=_("Upload CSV file"),
        help_text=_("Only accepts CSV file."),
        allow_empty_file=False,
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data["csv_file"]
        if not csv_file.name.endswith(".csv"):
            self.add_error("csv_file", CSV_ERRORS["only_csv"])
        try:
            csv_file.read().decode("UTF-8")
            csv_file.seek(0)  # set cursor back at the beginning of line
        except UnicodeDecodeError:
            self.add_error("csv_file", CSV_ERRORS["decoding"])
        return csv_file
