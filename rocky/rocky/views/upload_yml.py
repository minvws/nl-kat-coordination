import yaml
import io
from datetime import datetime, timezone
from typing import Any, ClassVar, TypedDict
from uuid import uuid4

import yaml.composer

from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView
from httpx import HTTPError
from pydantic import ValidationError
from tools.forms.upload_yml import YML_ERRORS
from tools.forms.upload_oois import  UploadOOIYMLForm

from octopoes.api.models import Declaration
from octopoes.models import OOI, Reference
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.dns.records import NXDOMAIN, DNSAAAARecord, DNSARecord, DNSCAARecord, \
    DNSCNAMERecord, DNSMXRecord, DNSNSRecord, DNSPTRRecord, DNSRecord, DNSSOARecord, DNSTXTRecord
from octopoes.models.ooi.email_security import DKIMExists, DKIMKey, DKIMSelector, DMARCTXTRecord, \
    DNSSPFMechanism, DNSSPFMechanismHostname, DNSSPFMechanismIP, DNSSPFMechanismNetBlock, DNSSPFRecord
from octopoes.models.ooi.findings import FindingType, ADRFindingType, CVEFindingType, CWEFindingType, \
    CAPECFindingType, RetireJSFindingType, SnykFindingType, KATFindingType, Finding, MutedFinding
from octopoes.models.ooi.geography import GeographicPoint
from octopoes.models.ooi.monitoring import Application, Incident
from octopoes.models.ooi.question import Question
from octopoes.models.ooi.reports import AssetReport, BaseReport, HydratedReport, Report, ReportData, ReportRecipe
from octopoes.models.ooi.scans import ExternalScan
from octopoes.models.ooi.dns.zone import DNSZone, Hostname, ResolvedHostname
from octopoes.models.ooi.network import AutonomousSystem, IPAddressV4, IPAddressV6, IPV4NetBlock, \
    IPV6NetBlock, NetBlock, Network, IPAddress, IPPort
from octopoes.models.ooi.web import URL, HostnameHTTPURL, WebURL, Website, IPAddressHTTPURL, HTTPResource, \
    HTTPHeader, HTTPHeaderURL, HTTPHeaderHostname, ImageMetadata, RESTAPI, APIDesignRule, APIDesignRuleResult, \
    SecurityTXT
from octopoes.models.ooi.service import Service, IPService, TLSCipher
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.ooi.certificate import SubjectAlternativeName, SubjectAlternativeNameHostname, \
    SubjectAlternativeNameIP, SubjectAlternativeNameQualifier, X509Certificate

from rocky.bytes_client import get_bytes_client

class OOICandidate(TypedDict):
    ooi_type: str

class YamlSchape(TypedDict):
    references: dict[str, dict]
    oois: list[dict[str, OOICandidate]]

YML_CRITERIA = [
    _(
        'All objects should be stored in "oois" list field at root level. '
        'Only objects under "oois" field will be created unless they are referenced by an object placed in "oois"'
    ),
    _("It can create various of object type in a single file"),
    _('Each object should contain an extra field called "ooi_type" that determines ooi type, it\'s case-sensitive'),
    _(
        "You can use YAML referencing. "
        'Storing referenced objects in the "references" field is suggested for the next possible updates.'
    ),
    _(
        "Don't use base OOI classes for better experience. For example use CWEFindingType instead of FindingType. "
        "At least FindingType id field should starts with CWE or other types and splitted with the '-' symbol."
    )
]

CLEARANCE_VALUES = ["0", "1", "2", "3", "4", 0,1,2,3,4]


class UploadYML(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    template_name = "upload_yml.html"
    form_class = UploadOOIYMLForm
    permission_required = "tools.can_scan_organization"
    reference_cache: dict[str, Any] = {"Network": {"internet": Network(name="internet")}}
    ooi_types: ClassVar[dict[str, Any]] = {
        # Records
        "DNSARecord": {"type": DNSARecord },
        "DNSAAAARecord": {"type": DNSAAAARecord },
        "DNSMXRecord": {"type": DNSMXRecord },
        "DNSTXTRecord": {"type": DNSTXTRecord },
        "DNSNSRecord": {"type": DNSNSRecord },
        "DNSCNAMERecord": {"type": DNSCNAMERecord },
        "DNSSOARecord": {"type": DNSSOARecord },
        "NXDOMAIN": {"type": NXDOMAIN },
        "DNSPTRRecord": {"type": DNSPTRRecord },
        "DNSCAARecord": {"type": DNSCAARecord },
        # Zone
        "DNSZone": {"type": DNSZone },
        "Hostname": {"type": Hostname },
        "ResolvedHostname": {"type": ResolvedHostname },
        # Certificate
        "X509Certificate": {"type": X509Certificate },
        "SubjectAlternativeNameHostname": {"type": SubjectAlternativeNameHostname },
        "SubjectAlternativeNameIP": {"type": SubjectAlternativeNameIP },
        "SubjectAlternativeNameQualifier": {"type": SubjectAlternativeNameQualifier },
        # Config
        "Config": {"type": Config },
        # Email Security
        "DNSSPFRecord": {"type": DNSSPFRecord },
        "DNSSPFMechanismIP": {"type": DNSSPFMechanismIP },
        "DNSSPFMechanismHostname": {"type": DNSSPFMechanismHostname },
        "DNSSPFMechanismNetBlock": {"type": DNSSPFMechanismNetBlock },
        "DMARCTXTRecord": {"type": DMARCTXTRecord },
        "DKIMExists": {"type": DKIMExists },
        "DKIMSelector": {"type": DKIMSelector },
        "DKIMKey": {"type": DKIMKey },
        # Findings
        # ?baseclass
        "FindingType": {"type": FindingType },
        "ADRFindingType": {"type": ADRFindingType },
        "CVEFindingType": {"type": CVEFindingType },
        "CWEFindingType": {"type": CWEFindingType },
        "CAPECFindingType": {"type": CAPECFindingType },
        "RetireJSFindingType": {"type": RetireJSFindingType },
        "SnykFindingType": {"type": SnykFindingType },
        "KATFindingType": {"type": KATFindingType },
        "Finding": {"type": Finding, "distinctive_fields": ["ooi", "finding_type"]},
        "MutedFinding": {"type": MutedFinding },
        # Geography
        "GeographicPoint": {"type": GeographicPoint, "distinctive_fields": ["ooi", "longitude", "latitude"]},
        # Monitoring
        "Application": {"type": Application },
        "Incident": {"type": Incident },
        # Network
        "Network": {"type": Network },
        # ?baseclass
        "IPAddress": {"type": IPAddress },
        "IPAddressV4": {"type": IPAddressV4 },
        "IPAddressV6": {"type": IPAddressV6 },
        "IPPort": {"type": IPPort },
        "AutonomousSystem": {"type": AutonomousSystem },
        # ?baseclass
        "NetBlock": {"type": NetBlock },
        "IPV6NetBlock": {"type": IPV6NetBlock },
        "IPV4NetBlock": {"type": IPV4NetBlock },
        # Question
        "Question": {"type": Question },
        # Reports
        "ReportData": {"type": ReportData },
        "AssetReport": {"type": AssetReport },
        "Report": {"type": Report },
        "HydratedReport": {"type": HydratedReport },
        "ReportRecipe": {"type": ReportRecipe },
        # Scans
        "ExternalScan": {"type": ExternalScan },
        # Service
        "Service": {"type": Service },
        "IPService": {"type": IPService },
        "TLSCipher": {"type": TLSCipher },
        # Software
        "Software": {"type": Software },
        "SoftwareInstance": {"type": SoftwareInstance },
        # Web
        "Website": {"type": Website },
        # ?baseclass
        "WebURL": {"type": WebURL, "distinctive_fields": ["scheme", "port", "path"]},
        "HostnameHTTPURL": {"type": HostnameHTTPURL },
        "IPAddressHTTPURL": {"type": IPAddressHTTPURL },
        "HTTPResource": {"type": HTTPResource },
        "HTTPHeader": {"type": HTTPHeader },
        "URL": {"type": URL },
        "HTTPHeaderURL": {"type": HTTPHeaderURL },
        "HTTPHeaderHostname": {"type": HTTPHeaderHostname },
        "ImageMetadata": {"type": ImageMetadata },
        "RESTAPI": {"type": RESTAPI },
        "APIDesignRule": {"type": APIDesignRule },
        "APIDesignRuleResult": {"type": APIDesignRuleResult },
        "SecurityTXT": {"type": SecurityTXT },
    }
    skip_properties = ("object_type", "scan_profile", "primary_key", "user_id")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not self.organization:
            self.add_error_notification(YML_ERRORS["no_org"])

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
        # filter base ooi classes from the "createable list"
        context['ooi_types'] = list(filter(
            None,
            map(
                lambda x: _(x) if x not in ["FindingType", "IPAddress", "NetBlock", "WebURL"] else None,
                self.ooi_types.keys()
            )
        ))
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

    def process_yml(self, form):
        yml_file = form.cleaned_data["yml_file"]
        yml_raw_data = yml_file.read()
        task_id = uuid4()
        get_bytes_client(self.organization.code).add_manual_proof(
            task_id, yml_raw_data, manual_mime_types={"manual/yml"}
        )
        yml_data = io.StringIO(yml_raw_data.decode("UTF-8"))
        refs_and_oois: YamlSchape
        try:
            refs_and_oois: YamlSchape = yaml.safe_load(yml_data)
        except yaml.composer.ComposerError as err:
            return self.add_error_notification(f"Corrupted yaml file imported. Error: {err}")
        oois_from_yaml = refs_and_oois["oois"]

        # Controlling shape of data
        if type(oois_from_yaml) != list:
            return self.add_error_notification("OOI's should be stored in list type in the \"oois\" root field.")
        if len(list(filter(lambda ooi_c: type(ooi_c) != dict, oois_from_yaml))):
            return self.add_error_notification("All elements of oois list should object to create OOI.")
        if len(list(filter(lambda ooi_c: len(ooi_c.keys()) < 1, oois_from_yaml))):
            return self.add_error_notification("There are unsupported objects in the file.")
        if len(list(filter(lambda ooi_c: ooi_c.get("ooi_type") not in self.ooi_types.keys(), oois_from_yaml))):
            return self.add_error_notification("Unsupported OOI type in the file. All OOI types are case sensitive")

        rows_with_error = []
        for ooi_number, ooi_dict in enumerate(oois_from_yaml, start=1):
            try:
                ooi = self.create_ooi(ooi_dict)
                self.octopoes_api_connector.save_declaration(
                    Declaration(ooi=ooi, valid_time=datetime.now(timezone.utc), task_id=task_id)
                )
            except ValidationError as err:
                rows_with_error.append(ooi_number)
                rows_with_error.append("ValidationError")
                rows_with_error.append(str(err))
            except ValueError as err:
                rows_with_error.append(ooi_number)
                rows_with_error.append("ValueError")
                rows_with_error.append(str(err))
            except KeyError as err:
                rows_with_error.append(ooi_number)
                rows_with_error.append("KeyError")
                rows_with_error.append(str(err))
                rows_with_error.append(str(err.args))
        if rows_with_error:
            message = _("Object(s) could not be created for index: ") + ", ".join(map(str, rows_with_error))
            return self.add_error_notification(message)
        self.add_success_notification(_("Object(s) successfully added."))

        
    def create_ooi(self, ooi_dict: dict):
        ooi_type = self.ooi_types[ooi_dict["ooi_type"]]["type"]
        # Special Cases
        # normally it shouldn't run cause of using ooi_type in each raw object. But if user define some how a base class in the
        # file it will come here and object will be created with proper subclass. exp: IPAddressV4 instead of IPAddress.
        if hasattr(ooi_type, 'type_from_raw'): ooi_type = ooi_type.type_from_raw(ooi_dict)
        # check for cache
        cache, cache_field_name = self.get_cache_and_field_name(ooi_type, ooi_dict)
        if cache_field_name in cache: return cache[cache_field_name]
        # creation process
        ooi_fields = [
            (field, field if model_field.annotation != Reference else model_field.json_schema_extra['object_type'], model_field.annotation == Reference, model_field.is_required())
            for field, model_field in ooi_type.__fields__.items()
            if field not in self.skip_properties
        ]
        kwargs: dict[str, Any] = {}
        for field, referenced_type, is_reference, required in ooi_fields:
            if is_reference and required or is_reference and ooi_dict.get(field):
                try:
                    self.ooi_types[referenced_type]['type']
                except Exception as e: raise Exception(e)
                # required referenced fields or not required but also defined in yaml
                try:
                    referenced_ooi = self.create_ooi(
                        ooi_dict.get(field.lower()) or ooi_dict[referenced_type.lower()],
                    )
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
            # required feilds or not required but also defined in yaml
            elif not is_reference and (required or not required and ooi_dict.get(field)):
                kwargs[field] = ooi_dict.get(field)
        ooi = ooi_type(**kwargs)
        # Save to cache
        cache[cache_field_name] = ooi
        # Set clearence
        if ooi_dict.get("clearance") in CLEARANCE_VALUES:
            self.raise_clearance_level(ooi.reference, int(ooi_dict["clearance"]))
        return ooi

    def get_distinctive_fields(self, ooi_type):
        return self.ooi_types[ooi_type.__name__].get('distinctive_fields', ooi_type._natural_key_attrs)
    
    def get_cache_and_field_name(self, ooi_type, ooi_dict):
        dins_fields = self.get_distinctive_fields(ooi_type)
        cache_field_name = self.get_cache_name(ooi_dict, dins_fields)
        cache = self.reference_cache.setdefault(ooi_type.__name__, {})
        return cache, cache_field_name

    def get_cache_name(self, ooi_dict:dict, field_combination: list[str]):
        """It creates name for cache from str values of distinctive fields"""
        return "|".join(filter(None, map(lambda a: str(ooi_dict.get(a, "")), field_combination)))
