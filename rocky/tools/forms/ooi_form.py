from datetime import datetime, timezone
from enum import Enum
from inspect import isclass
from ipaddress import IPv4Address, IPv6Address
from typing import Literal, Union, get_args, get_origin

from django import forms
from django.utils.translation import gettext_lazy as _
from pydantic import AnyUrl, JsonValue
from pydantic.fields import FieldInfo

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models.ooi.question import Question
from octopoes.models.types import get_collapsed_types, get_relations
from tools.forms.base import BaseRockyForm, CheckboxGroup
from tools.forms.settings import CLEARANCE_TYPE_CHOICES
from tools.models import SCAN_LEVEL


class OOIForm(BaseRockyForm):
    def __init__(self, ooi_class: type[OOI], connector: OctopoesAPIConnector, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ooi_class = ooi_class
        self.api_connector = connector
        self.initial = kwargs.get("initial", {})

        fields = self.get_fields()
        for name, field in fields.items():
            self.fields[name] = field

    def clean(self):
        return {key: value for key, value in super().clean().items() if value}

    def get_fields(self) -> dict[str, forms.fields.Field]:
        return self.generate_form_fields()

    def generate_form_fields(
        self,
        hidden_ooi_fields: dict[str, str] | None = None,
    ) -> dict[str, forms.fields.Field]:
        fields = {}
        for name, field in self.ooi_class.model_fields.items():
            annotation = field.annotation
            default_attrs = default_field_options(name, field)
            # if annotation is an Union, get the first non-optional type
            optional_type = get_args(annotation)[0] if get_origin(annotation) == Union else None

            if name == "primary_key":
                continue

            # skip literals
            if hasattr(annotation, "__origin__") and annotation.__origin__ == Literal:
                continue

            # skip scan_profile
            if name == "scan_profile":
                continue

            if hidden_ooi_fields and name in hidden_ooi_fields:
                # Hidden ooi fields will have the value of an OOI ID
                fields[name] = forms.CharField(widget=forms.HiddenInput())
            elif name in get_relations(self.ooi_class):
                fields[name] = generate_select_ooi_field(
                    self.api_connector,
                    name,
                    field,
                    get_relations(self.ooi_class)[name],
                    self.initial.get(name, None),
                )
            elif annotation in [IPv4Address, IPv6Address]:
                fields[name] = generate_ip_field(field)
            elif annotation == AnyUrl:
                fields[name] = generate_url_field(field)
            elif (
                annotation == dict
                or annotation == dict[str, str]
                or annotation == list[str]
                or annotation == dict[str, JsonValue]
            ):
                fields[name] = forms.JSONField(**default_attrs)
            elif annotation == int or (hasattr(annotation, "__args__") and int in annotation.__args__):
                fields[name] = forms.IntegerField(**default_attrs)
            elif isclass(annotation) and issubclass(annotation, Enum):
                fields[name] = generate_select_ooi_type(name, annotation, field)
            elif self.ooi_class == Question and name == "json_schema":
                fields[name] = forms.CharField(**default_attrs)
            elif isclass(annotation) and issubclass(annotation, str) or optional_type is str:
                if name in self.ooi_class.__annotations__ and self.ooi_class.__annotations__[name] == dict[str, str]:
                    fields[name] = forms.JSONField(**default_attrs)
                else:
                    fields[name] = forms.CharField(
                        max_length=256, **default_attrs, empty_value=None if not field.is_required() else ""
                    )
            else:
                fields[name] = forms.CharField(max_length=256, **default_attrs)

        return fields


def generate_select_ooi_field(
    api_connector: OctopoesAPIConnector,
    name: str,
    field: FieldInfo,
    related_ooi_type: type[OOI],
    initial: str | None = None,
) -> forms.fields.Field:
    # field is a relation, query all objects, and build select
    default_attrs = default_field_options(name, field)
    is_multiselect = getattr(field.annotation, "__origin__", None) == list
    option_label = default_attrs.get("label", _("option"))

    option_text = "-- " + _("Optionally choose a {option_label}").format(option_label=option_label) + " --"
    if field.is_required():
        option_text = "-- " + _("Please choose a {option_label}").format(option_label=option_label) + " --"

    # Generate select options
    select_options = [] if is_multiselect else [("", option_text)]

    if initial:
        select_options.append((initial, initial))

    oois = api_connector.list_objects({related_ooi_type}, datetime.now(timezone.utc)).items
    select_options.extend([(ooi.primary_key, ooi.primary_key) for ooi in oois])

    if is_multiselect:
        return forms.MultipleChoiceField(
            widget=forms.SelectMultiple(), choices=select_options, initial=initial, **default_attrs
        )

    return forms.CharField(widget=forms.Select(choices=select_options), **default_attrs)


def generate_select_ooi_type(name: str, enumeration: type[Enum], field: FieldInfo) -> forms.fields.Field:
    """OOI Type (enum) fields will have a select input"""
    default_attrs = default_field_options(name, field)
    choices = [(entry.value, entry.name) for entry in list(enumeration)]

    return forms.CharField(widget=forms.Select(choices=choices), **default_attrs)


def generate_ip_field(field: FieldInfo) -> forms.fields.Field:
    """IPv4 and IPv6 fields will have a text input"""
    default_attrs = default_field_options("", field)
    protocol = "IPv4" if field.annotation == IPv4Address else "IPv6"
    return forms.GenericIPAddressField(protocol=protocol, **default_attrs)


def generate_url_field(field: FieldInfo) -> forms.fields.Field:
    """URL fields will have a text input"""
    default_attrs = default_field_options("", field)
    if default_attrs.get("label") == "raw":
        default_attrs.update({"label": "URL"})
    field = forms.URLField(**default_attrs)
    field.widget.attrs.update({"placeholder": "https://example.org"})
    return field


def default_field_options(name: str, field_info: FieldInfo) -> dict[str, str | bool]:
    return {
        "label": name,
        "required": field_info.is_required(),
    }


class ClearanceFilterForm(BaseRockyForm):
    clearance_level = forms.CharField(
        label=_("Filter by clearance level"),
        widget=CheckboxGroup(choices=SCAN_LEVEL.choices),
        required=False,
    )

    clearance_type = forms.CharField(
        label=_("Filter by clearance type"),
        widget=CheckboxGroup(choices=CLEARANCE_TYPE_CHOICES),
        required=False,
    )


_EXCLUDED_OOI_TYPES = ("Finding", "FindingType")

SORTED_OOI_TYPES = sorted(
    [
        ooi_class.get_ooi_type()
        for ooi_class in get_collapsed_types()
        if ooi_class.get_ooi_type() not in _EXCLUDED_OOI_TYPES
    ]
)

OOI_TYPE_CHOICES = ((ooi_type, ooi_type) for ooi_type in SORTED_OOI_TYPES)


class OOITypeMultiCheckboxForm(BaseRockyForm):
    ooi_type = forms.MultipleChoiceField(
        label=_("Filter by OOI types"),
        required=False,
        choices=OOI_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )
