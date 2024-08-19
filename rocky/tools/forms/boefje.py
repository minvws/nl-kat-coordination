from django import forms
from django.utils.translation import gettext_lazy as _

from tools.forms.settings import FINDING_DATETIME_HELP_TEXT, SCAN_LEVEL_CHOICES


class BoefjeAddForm(forms.Form):
    container_image = forms.CharField(
        required=False,
        label=_("Container image"),
        widget=forms.Textarea(attrs={"rows": 1}),
    )
    name = forms.CharField(
        required=False,
        label=_("Name"),
        widget=forms.Textarea(attrs={"rows": 1}),
    )
    description = forms.CharField(
        required=False,
        label=_("Description"),
        widget=forms.Textarea(attrs={"placeholder": _("Describe your Boefje"), "rows": 3}),
    )
    arguments = forms.CharField(
        required=False,
        label=_("Arguments"),
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    json_schema = forms.JSONField(
        label=_("JSON schema"),
        widget=forms.Textarea(attrs={"placeholder": '{"key": "value"}', "rows": 10, "cols": 40}),
    )
    input_object_types = forms.CharField(
        required=False,
        label=_("Input object types"),
        widget=forms.Select(choices=SCAN_LEVEL_CHOICES),
        help_text=FINDING_DATETIME_HELP_TEXT,
    )
    clearance_level = forms.CharField(
        required=False,
        label=_("Clearance level"),
        widget=forms.Select(choices=SCAN_LEVEL_CHOICES),
        help_text=FINDING_DATETIME_HELP_TEXT,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
