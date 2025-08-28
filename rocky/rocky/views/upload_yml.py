import io
from datetime import datetime, timezone
from typing import Any, ClassVar, TypedDict
from uuid import uuid4

import yaml
import yaml.composer
import yaml.parser
from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView
from pydantic import ValidationError
from tools.forms.upload_oois import UploadOOIYMLForm

from octopoes.api.models import Declaration
from octopoes.models import Reference
from octopoes.models.ooi.certificate import SubjectAlternativeName
from octopoes.models.ooi.dns.records import DNSRecord
from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.ooi.geography import GeographicPoint
from octopoes.models.ooi.network import IPAddress, NetBlock, Network
from octopoes.models.ooi.web import WebURL
from octopoes.models.types import OOI_TYPES
from rocky.bytes_client import get_bytes_client


class OOICandidate(dict):
    ooi_type: str
    clearance: int


class YAMLData(TypedDict):
    references: dict[str, dict]
    oois: list[OOICandidate]


YML_CRITERIA = [
    _(
      'All objects should be stored in the "oois" list at the root level. '
      'Only objects under the "oois" field will be created, unless they are referenced by an object within "oois".'
    ),
    _("Objects of various types can be included in a single file."),
    _(
      'Each object must contain an additional field called "ooi_type", which specifies the object type. '
      'This field is case-sensitive.'),
    _(
      "YAML referencing is supported. "
      'It is recommended to store referenced objects in the "references" field to facilitate potential future updates.'
    ),
]

CLEARANCE_VALUES = ["0", "1", "2", "3", "4", 0, 1, 2, 3, 4]

# Some OOI types cannot instantiated
banned_ooi_classes = [
    "FindingType",
    "IPAddress",
    "NetBlock",
    "WebURL",
    "DNSRecord",
    "DNSSPFMechanism",
    "SubjectAlternativeName",
    "BaseReport",
    "ReportData",
    "AssetReport",
    "Report",
    "HydratedReport",
    "ReportRecipe",
]


def get_cache_name(ooi_dict: dict, field_combination: list[str]):
    """It creates name for cache from str values of distinctive fields"""
    return "|".join(filter(None, map(lambda a: str(ooi_dict.get(a, "")), field_combination)))


class UploadYML(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    template_name = "upload_yml.html"
    form_class = UploadOOIYMLForm
    permission_required = "tools.can_scan_organization"
    reference_cache: dict[str, Any] = {"Network": {"internet": Network(name="internet")}}
    ooi_types: ClassVar[dict[str, Any]] = {
        ooi_type: {"type": OOI_TYPES[ooi_type]} for ooi_type in OOI_TYPES if ooi_type not in banned_ooi_classes
    }
    # Types without _natural_key_attrs and some base OOI classes have type_from_raw class method
    ooi_types["GeographicPoint"] = {"type": GeographicPoint, "distinctive_fields": ["ooi", "longitude", "latitude"]}
    ooi_types["Finding"] = {"type": Finding, "distinctive_fields": ["ooi", "finding_type"]}
    ooi_types["WebURL"] = {"type": WebURL, "distinctive_fields": ["scheme", "port", "path"]}
    ooi_types["SubjectAlternativeName"] = {"type": SubjectAlternativeName}
    ooi_types["FindingType"] = {"type": FindingType}
    ooi_types["IPAddress"] = {"type": IPAddress}
    ooi_types["NetBlock"] = {"type": NetBlock}
    ooi_types["DNSRecord"] = {"type": DNSRecord}

    skip_properties = ("object_type", "scan_profile", "primary_key", "user_id")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("ooi_list", kwargs={"organization_code": self.organization.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list", kwargs={"organization_code": self.organization.code}), "text": _("Objects")},
            {
                "url": reverse("upload_yml", kwargs={"organization_code": self.organization.code}),
                "text": _("Upload YAML"),
            },
        ]
        context["criteria"] = YML_CRITERIA
        # filter base ooi classes from the "creatable list"
        context["ooi_types"] = list(
            filter(None, map(lambda x: _(x) if x not in banned_ooi_classes else None, self.ooi_types.keys()))
        )
        context["base_ooi_types"] = [
            "Following is about base OOI types "
            "(an example of base OOI class or type can be FindingType and it is base for CWEFindingType and more). "
            "Base OOI classes are not recommended for better experience. "
            "They have different prerequisites to turn them into one of their child class types.",
            "IPAddress base type automatically switch to IPAddressV4 or IPAddressV6 according to address field.",
            "NetBlock base type automatically switch to IPV4NetBlock or IPV6NetBlock according to start_ip field.",
            "DNSRecord base type automatically switch to proper class according to dns_record_type field.",
            "WebUrl base type should have netloc field. "
            "According to netloc (Hostname or IPv4Address en IPv6Address) "
            "it will turn into HostnameHTTPURL or IPAddressHTTPURL.",
            "SubjectAlternativeName base type should have proper fields to define as one of child types.",
            'FindingType base type should have an id field that contains "<SubclassName>-..."',
        ]
        return context

    def form_valid(self, form):
        if not self.process_yml(form):
            return redirect("upload_yml", organization_code=self.organization.code)
        return super().form_valid(form)

    def add_error_notification(self, error_message):
        messages.add_message(self.request, messages.ERROR, error_message)
        return False

    def add_success_notification(self, success_message):
        messages.add_message(self.request, messages.SUCCESS, success_message)
        return True

    def read_file(self, yml_file):
        try:
            bytes_from_file = yml_file.read()
            return bytes_from_file
        except UnicodeDecodeError:
            self.add_error_notification("File could not be decoded)")

    def process_yml(self, form):
        yml_file = form.cleaned_data["yml_file"]
        yml_raw_data = self.read_file(yml_file)
        if not yml_raw_data:
            return
        task_id = uuid4()
        get_bytes_client(self.organization.code).add_manual_proof(
            task_id, yml_raw_data, manual_mime_types={"manual/yml"}
        )
        yml_data = io.StringIO(yml_raw_data.decode("UTF-8"))
        try:
            refs_and_oois: YAMLData = yaml.safe_load(yml_data)
        except yaml.composer.ComposerError as err:
            return self.add_error_notification(f"Corrupted yaml file imported. Error: {err}")
        except yaml.parser.ParserError as err:
            return self.add_error_notification(f"Corrupted yaml file imported. Error: {err}")
        oois_from_yaml = refs_and_oois["oois"]

        # Controlling shape of data # con
        if type(oois_from_yaml) is not list:
            return self.add_error_notification('OOI\'s should be stored in list type in the "oois" root field.')
        if any(type(ooi_c) is not dict for ooi_c in oois_from_yaml):
            return self.add_error_notification("All elements of oois list should object to create OOI.")
        if any(len(ooi_c.keys()) < 1 for ooi_c in oois_from_yaml):
            return self.add_error_notification("There are unsupported objects in the file.")
        if any(ooi_c.get("ooi_type") not in self.ooi_types for ooi_c in oois_from_yaml):
            return self.add_error_notification("Unsupported OOI type in the file. All OOI types are case sensitive")

        rows_with_error = []
        for ooi_number, ooi_dict in enumerate(oois_from_yaml):
            try:
                ooi = self.create_ooi(ooi_dict)
                self.octopoes_api_connector.save_declaration(
                    Declaration(ooi=ooi, valid_time=datetime.now(timezone.utc), task_id=task_id)
                )
            except (ValidationError, ValueError, KeyError) as err:
                rows_with_error.extend([ooi_number, ooi_dict["ooi_type"], err.__repr__(), err, err.args])
        if rows_with_error:
            message = _("Object(s) could not be created for index: ") + ", ".join(map(str, rows_with_error))
            return self.add_error_notification(message)
        self.add_success_notification(_("Object(s) successfully added."))

    def create_ooi(self, ooi_dict: OOICandidate):
        ooi_type = self.ooi_types[ooi_dict["ooi_type"]]["type"]
        # Special Cases
        ooi_type = ooi_type.type_from_raw(ooi_dict)
        # check for cache
        cache, cache_field_name = self.get_cache_and_field_name(ooi_type, ooi_dict)
        if cache_field_name in cache:
            return cache[cache_field_name]
        # creation process
        ooi_fields = [
            (
                field,
                field if model_field.annotation != Reference else model_field.json_schema_extra["object_type"],
                model_field.annotation == Reference,
                model_field.is_required(),
            )
            for field, model_field in ooi_type.__fields__.items()
            if field not in self.skip_properties
        ]
        kwargs: dict[str, Any] = {}
        for field, referenced_type, is_reference, required in ooi_fields:
            if is_reference and required or is_reference and ooi_dict.get(field):
                # required referenced fields or not required but also defined in yaml
                try:
                    referenced_ooi = self.create_ooi(ooi_dict.get(field.lower()) or ooi_dict[referenced_type.lower()])
                    self.octopoes_api_connector.save_declaration(
                        Declaration(ooi=referenced_ooi, valid_time=datetime.now(timezone.utc))
                    )
                    kwargs[field] = referenced_ooi.reference
                except IndexError:
                    if required:
                        raise IndexError(
                            f"Required referenced primary-key field '{field}' not set "
                            f"and no default present for Type '{ooi_type.__name__}'."
                        )
                    else:
                        kwargs[field] = None
            # not required and not defined referenced field still in loop. they skipped with "not is_reference"
            # required fields or not required but also defined in yaml
            elif not is_reference and (required or not required and ooi_dict.get(field)):
                kwargs[field] = ooi_dict.get(field)
        ooi = ooi_type(**kwargs)
        # Save to cache
        cache[cache_field_name] = ooi
        # Set clearence
        if ooi_dict.get("clearance") in CLEARANCE_VALUES:
            self.raise_clearance_level(ooi.reference, int(ooi_dict["clearance"]))
        return ooi

    def get_cache_and_field_name(self, ooi_type, ooi_dict):
        dins_fields = self.ooi_types[ooi_type.__name__].get("distinctive_fields", ooi_type._natural_key_attrs)
        cache_field_name = get_cache_name(ooi_dict, dins_fields)
        cache = self.reference_cache.setdefault(ooi_type.__name__, {})
        return cache, cache_field_name
