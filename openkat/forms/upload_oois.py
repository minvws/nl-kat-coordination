from django import forms
from django.utils.translation import gettext as _

from openkat.forms.settings import BLANK_CHOICE
from openkat.forms.upload_csv import UploadCSVForm

OOI_TYPE_CHOICES = [
    BLANK_CHOICE,
    ("URL", "URL"),
    ("Hostname", "Hostname"),
    ("IPAddressV4", "IPAddressV4"),
    ("IPAddressV6", "IPAddressV6"),
]


class UploadOOICSVForm(UploadCSVForm):
    object_type = forms.ChoiceField(
        label=_("Object Type"),
        choices=OOI_TYPE_CHOICES,
        help_text=_("Choose a type of which objects are added."),
        required=True,
    )
