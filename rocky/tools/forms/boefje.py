from django import forms
from django.utils.translation import gettext_lazy as _
from katalogus.client import Boefje, DuplicateNameError, KATalogusClientV1

from octopoes.models.types import ALL_TYPES, type_by_name
from tools.enums import SCAN_LEVEL
from tools.forms.base import BaseRockyForm
from tools.forms.settings import (
    BOEFJE_CONSUMES_HELP_TEXT,
    BOEFJE_CONTAINER_IMAGE_HELP_TEXT,
    BOEFJE_DESCRIPTION_HELP_TEXT,
    BOEFJE_PRODUCES_HELP_TEXT,
    BOEFJE_SCAN_LEVEL_HELP_TEXT,
    BOEFJE_SCHEMA_HELP_TEXT,
)

OOI_TYPE_CHOICES = sorted((ooi_type.get_object_type(), ooi_type.get_object_type()) for ooi_type in ALL_TYPES)


class BoefjeSetupForm(BaseRockyForm):
    oci_image = forms.CharField(
        required=True,
        label=_("Container image"),
        help_text=BOEFJE_CONTAINER_IMAGE_HELP_TEXT,
    )
    name = forms.CharField(
        required=True,
        label=_("Name"),
    )
    description = forms.CharField(
        required=False,
        label=_("Description"),
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=BOEFJE_DESCRIPTION_HELP_TEXT,
    )
    oci_arguments = forms.CharField(
        required=False,
        label=_("Arguments"),
        widget=forms.TextInput(
            attrs={"description": "For example: -sTU --top-ports 1000", "aria-describedby": "input-description"}
        ),
    )
    boefje_schema = forms.JSONField(
        required=False,
        label=_("JSON Schema"),
        help_text=BOEFJE_SCHEMA_HELP_TEXT,
    )
    consumes = forms.CharField(
        required=False,
        label=_("Input object type"),
        widget=forms.SelectMultiple(choices=OOI_TYPE_CHOICES),
        help_text=BOEFJE_CONSUMES_HELP_TEXT,
    )
    produces = forms.CharField(
        required=False,
        label=_("Output mime types"),
        help_text=BOEFJE_PRODUCES_HELP_TEXT,
    )
    scan_level = forms.CharField(
        required=False,
        label=_("Clearance level"),
        widget=forms.Select(choices=SCAN_LEVEL.choices),
        help_text=BOEFJE_SCAN_LEVEL_HELP_TEXT,
    )

    def __init__(self, katalogus_client: KATalogusClientV1, plugin_id: str, created: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.katalogus_client = katalogus_client
        self.plugin_id = plugin_id
        self.created = created

    def create_boefje_with_form_data(self, form_data, plugin_id: str, created: str):
        arguments = [] if form_data["oci_arguments"] == "" else form_data["oci_arguments"].split()
        consumes = [] if form_data["consumes"] == "" else form_data["consumes"].strip("[]").replace("'", "").split(", ")
        produces = [] if form_data["produces"] == "" else form_data["produces"].split(",")
        produces = [p.strip() for p in produces]
        input_objects = []

        for input_object in consumes:
            input_objects.append(type_by_name(input_object))

        return Boefje(
            id=plugin_id,
            name=form_data["name"],
            created=created,
            description=form_data["description"],
            enabled=False,
            type="boefje",
            scan_level=form_data["scan_level"],
            consumes=input_objects,
            produces=produces,
            boefje_schema=form_data["boefje_schema"],
            oci_image=form_data["oci_image"],
            oci_arguments=arguments,
        )


class BoefjeAddForm(BoefjeSetupForm):
    def clean(self):
        cleaned_data = super().clean()

        plugin = self.create_boefje_with_form_data(cleaned_data, self.plugin_id, self.created)

        try:
            self.katalogus_client.create_plugin(plugin)
        except DuplicateNameError:
            handle_existing_name(self, plugin.name)
        return cleaned_data


class BoefjeEditForm(BoefjeSetupForm):
    def clean(self):
        cleaned_data = super().clean()

        plugin = self.create_boefje_with_form_data(cleaned_data, self.plugin_id, self.created)

        try:
            self.katalogus_client.edit_plugin(plugin)
        except DuplicateNameError:
            handle_existing_name(self, plugin.name)

        return cleaned_data


def handle_existing_name(self, plugin_name):
    self.add_error("name", _("Boefje with name '%s' does already exist. Please choose another name.") % plugin_name)
