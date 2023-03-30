from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import Type, Dict, Union, List

from django import forms
from django.utils.translation import gettext_lazy as _
from pydantic import AnyUrl
from pydantic.fields import ModelField, SHAPE_LIST

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models.types import get_relations
from tools.forms.base import BaseRockyForm, CheckboxGroup
from tools.forms.settings import CLEARANCE_TYPE_CHOICES
from tools.models import SCAN_LEVEL


class OOIForm(BaseRockyForm):
    def __init__(self, ooi_class: Type[OOI], connector: OctopoesAPIConnector, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ooi_class = ooi_class
        self.api_connector = connector

        fields = self.get_fields()
        for name, field in fields.items():
            self.fields[name] = field

    def clean(self):
        return {key: value for key, value in super().clean().items() if value != ""}

    def get_fields(self) -> Dict[str, forms.fields.Field]:
        return self.generate_form_fields()

    def generate_form_fields(
        self,
        hidden_ooi_fields: Dict[str, str] = None,
    ) -> Dict[str, forms.fields.Field]:
        fields = {}
        for name, field in self.ooi_class.__fields__.items():
            default_attrs = default_field_options(field)

            if name == "primary_key":
                continue

            if not hasattr(field.type_, "mro"):  # Literals
                continue

            if hidden_ooi_fields and name in hidden_ooi_fields.keys():
                # Hidden ooi fields will have the value of an OOI ID
                fields[name] = forms.CharField(widget=forms.HiddenInput())
            elif field.name in get_relations(self.ooi_class):
                fields[name] = generate_select_ooi_field(
                    self.api_connector, field, get_relations(self.ooi_class)[field.name]
                )
            elif field.type_ in [IPv4Address, IPv6Address]:
                fields[name] = generate_ip_field(field)
            elif field.type_ == AnyUrl:
                fields[name] = generate_url_field(field)
            elif field.type_ == int or int in field.type_.mro():
                fields[name] = forms.IntegerField(**default_attrs)
            elif issubclass(field.type_, Enum):
                fields[name] = generate_select_ooi_type(field)
            elif issubclass(field.type_, str):
                fields[name] = forms.CharField(max_length=256, **default_attrs)

        return fields


def generate_select_ooi_field(
    api_connector: OctopoesAPIConnector, field: ModelField, related_ooi_type: Type[OOI]
) -> forms.fields.Field:
    """Select field will have a list of OOIs"""
    # field is a relation, query all objects, and build select
    default_attrs = default_field_options(field)
    is_multiselect = field.shape == SHAPE_LIST
    option_label = default_attrs.get("label", _("option"))

    option_text = "-- " + _("Optionally choose a {option_label}").format(option_label=option_label) + " --"

    if field.required:
        option_text = "-- " + _("Please choose a {option_label}").format(option_label=option_label) + " --"

    # Generate select options
    select_options = [] if is_multiselect else [("", option_text)]
    oois = api_connector.list({related_ooi_type}).items
    select_options.extend([(ooi.primary_key, ooi.primary_key) for ooi in oois])

    if is_multiselect:
        return forms.MultipleChoiceField(widget=forms.SelectMultiple(), choices=select_options, **default_attrs)

    return forms.CharField(widget=forms.Select(choices=select_options), **default_attrs)


def generate_select_ooi_type(field: ModelField) -> forms.fields.Field:
    """OOI Type (enum) fields will have a select input"""
    default_attrs = default_field_options(field)
    choices = [(val.value, val.value) for val in field.type_]
    return forms.CharField(widget=forms.Select(choices=choices), **default_attrs)


def generate_ip_field(field: ModelField) -> forms.fields.Field:
    """IPv4 and IPv6 fields will have a text input"""
    default_attrs = default_field_options(field)
    protocol = "IPv4" if field.type_ == IPv4Address else "IPv6"
    return forms.GenericIPAddressField(protocol=protocol, **default_attrs)


def generate_url_field(field: ModelField) -> forms.fields.Field:
    """URL fields will have a text input"""
    default_attrs = default_field_options(field)
    if default_attrs.get("label") == "raw":
        default_attrs.update({"label": "URL"})
    field = forms.URLField(**default_attrs)
    field.widget.attrs.update({"placeholder": "https://example.org"})
    return field


def default_field_options(field: ModelField) -> Dict[str, Union[str, bool]]:
    return {
        "label": field.name,
        "required": bool(field.required),
    }


class ClearanceFilterForm(BaseRockyForm):
    clearance_level = forms.CharField(
        label="Filter by clearance level",
        widget=CheckboxGroup(toggle_all_button=True, choices=SCAN_LEVEL.choices),
        required=False,
    )

    clearance_type = forms.CharField(
        label="Filter by clearance type",
        widget=CheckboxGroup(toggle_all_button=True, choices=CLEARANCE_TYPE_CHOICES),
        required=False,
    )

    def __init__(self, clearance_level: List[str], selected_clearance_types: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["clearance_level"].initial = clearance_level
        self.fields["clearance_type"].initial = selected_clearance_types
