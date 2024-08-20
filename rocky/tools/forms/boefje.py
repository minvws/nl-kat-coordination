from django import forms
from django.utils.translation import gettext_lazy as _

from octopoes.models.types import ALL_TYPES
from tools.enums import SCAN_LEVEL
from tools.forms.base import BaseRockyForm
from tools.forms.settings import FINDING_DATETIME_HELP_TEXT

OOI_TYPE_CHOICES = ((ooi_type.get_object_type(), ooi_type.get_object_type()) for ooi_type in ALL_TYPES)

JSON_SCHEMA = {
    "id": "string",
    "name": "string",
    "version": "string",
    "created": "2024-08-19T15:13:27.352Z",
    "description": "string",
    "environment_keys": ["string"],
    "enabled": "boolean",
    "static": "boolean",
    "type": "boefje",
    "scan_level": 1,
    "consumes": ["string"],
    "produces": ["string"],
    "runnable_hash": "string",
    "oci_image": "string",
    "oci_arguments": ["string"],
}


class BoefjeAddForm(BaseRockyForm):
    container_image = forms.CharField(
        required=False,
        label=_("Container image"),
        widget=forms.TextInput(attrs={"rows": 1}),
    )
    name = forms.CharField(
        required=False,
        label=_("Name"),
        widget=forms.TextInput(attrs={"rows": 1}),
    )
    description = forms.CharField(
        required=False,
        label=_("Description"),
        widget=forms.Textarea(attrs={"placeholder": _("Placeholder"), "rows": 3}),
    )
    arguments = forms.CharField(
        required=False,
        label=_("Arguments"),
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    json_schema = forms.JSONField(
        required=True,
        label=_("Json schema"),
        widget=forms.Textarea(attrs={"rows": 10, "cols": 40}),
        initial=JSON_SCHEMA,
    )
    object_type = forms.CharField(
        required=False,
        label=_("Object type"),
        widget=forms.Select(choices=OOI_TYPE_CHOICES),
    )
    clearance_level = forms.CharField(
        required=False,
        label=_("Clearance level"),
        widget=forms.Select(choices=SCAN_LEVEL.choices),
        help_text=FINDING_DATETIME_HELP_TEXT,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
