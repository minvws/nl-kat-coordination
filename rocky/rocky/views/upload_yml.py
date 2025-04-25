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
        "All objects should stored in list type initialy. It's list of map. "
        "Each map called main OOI object that kind of named object."
    ),
    _("Each main object begins with its name and names should correspond with OOI types in a case-sensitive manner."),
    _( "Subfields should be lower-case"),
    _("It can create various of object type in a single file"),
]

CLEARANCE_VALUES = ["0", "1", "2", "3", "4", 0,1,2,3,4]


class UploadYML(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    template_name = "upload_yml.html"
    form_class = UploadOOIYMLForm
    permission_required = "tools.can_scan_organization"
    reference_cache: dict[str, Any] = {"Network": {"internet": Network(name="internet")}}
    ooi_types: ClassVar[dict[str, Any]] = {
        # Records
        "DNSARecord": {"type": DNSARecord, "distinctive_fields": DNSARecord._natural_key_attrs},
        "DNSAAAARecord": {"type": DNSAAAARecord, "distinctive_fields": DNSAAAARecord._natural_key_attrs},
        "DNSMXRecord": {"type": DNSMXRecord, "distinctive_fields": DNSMXRecord._natural_key_attrs},
        "DNSTXTRecord": {"type": DNSTXTRecord, "distinctive_fields": DNSTXTRecord._natural_key_attrs},
        "DNSNSRecord": {"type": DNSNSRecord, "distinctive_fields": DNSNSRecord._natural_key_attrs},
        "DNSCNAMERecord": {"type": DNSCNAMERecord, "distinctive_fields": DNSCNAMERecord._natural_key_attrs},
        "DNSSOARecord": {"type": DNSSOARecord, "distinctive_fields": DNSSOARecord._natural_key_attrs},
        "NXDOMAIN": {"type": NXDOMAIN, "distinctive_fields": NXDOMAIN._natural_key_attrs},
        "DNSPTRRecord": {"type": DNSPTRRecord, "distinctive_fields": DNSPTRRecord._natural_key_attrs},
        "DNSCAARecord": {"type": DNSCAARecord, "distinctive_fields": DNSCAARecord._natural_key_attrs},
        # Zone
        "DNSZone": {"type": DNSZone, "distinctive_fields": DNSZone._natural_key_attrs},
        "Hostname": {"type": Hostname, "distinctive_fields": Hostname._natural_key_attrs},
        "ResolvedHostname": {"type": ResolvedHostname, "distinctive_fields": ResolvedHostname._natural_key_attrs},
        # Certificate
        "X509Certificate": {"type": X509Certificate, "distinctive_fields": X509Certificate._natural_key_attrs},
        "SubjectAlternativeNameHostname": {"type": SubjectAlternativeNameHostname, "distinctive_fields": SubjectAlternativeNameHostname._natural_key_attrs},
        "SubjectAlternativeNameIP": {"type": SubjectAlternativeNameIP, "distinctive_fields": SubjectAlternativeNameIP._natural_key_attrs},
        "SubjectAlternativeNameQualifier": {"type": SubjectAlternativeNameQualifier, "distinctive_fields": SubjectAlternativeNameQualifier._natural_key_attrs},
        # Config
        "Config": {"type": Config, "distinctive_fields": Config._natural_key_attrs},
        # Email Security
        "DNSSPFRecord": {"type": DNSSPFRecord, "distinctive_fields": DNSSPFRecord._natural_key_attrs},
        "DNSSPFMechanismIP": {"type": DNSSPFMechanismIP, "distinctive_fields": DNSSPFMechanismIP._natural_key_attrs},
        "DNSSPFMechanismHostname": {"type": DNSSPFMechanismHostname, "distinctive_fields": DNSSPFMechanismHostname._natural_key_attrs},
        "DNSSPFMechanismNetBlock": {"type": DNSSPFMechanismNetBlock, "distinctive_fields": DNSSPFMechanismNetBlock._natural_key_attrs},
        "DMARCTXTRecord": {"type": DMARCTXTRecord, "distinctive_fields": DMARCTXTRecord._natural_key_attrs},
        "DKIMExists": {"type": DKIMExists, "distinctive_fields": DKIMExists._natural_key_attrs},
        "DKIMSelector": {"type": DKIMSelector, "distinctive_fields": DKIMSelector._natural_key_attrs},
        "DKIMKey": {"type": DKIMKey, "distinctive_fields": DKIMKey._natural_key_attrs},
        # Findings
        # ?baseclass :: referenced at Finding :: TypeFromRaw added
        "FindingType": {"type": FindingType, "distinctive_fields": FindingType._natural_key_attrs},
        "ADRFindingType": {"type": ADRFindingType, "distinctive_fields": ADRFindingType._natural_key_attrs},
        "CVEFindingType": {"type": CVEFindingType, "distinctive_fields": CVEFindingType._natural_key_attrs},
        "CWEFindingType": {"type": CWEFindingType, "distinctive_fields": CWEFindingType._natural_key_attrs},
        "CAPECFindingType": {"type": CAPECFindingType, "distinctive_fields": CAPECFindingType._natural_key_attrs},
        "RetireJSFindingType": {"type": RetireJSFindingType, "distinctive_fields": RetireJSFindingType._natural_key_attrs},
        "SnykFindingType": {"type": SnykFindingType, "distinctive_fields": SnykFindingType._natural_key_attrs},
        "KATFindingType": {"type": KATFindingType, "distinctive_fields": KATFindingType._natural_key_attrs},
        "Finding": {"type": Finding, "distinctive_fields": ["ooi", "finding_type"]},
        "MutedFinding": {"type": MutedFinding, "distinctive_fields": MutedFinding._natural_key_attrs},
        # Geography
        "GeographicPoint": {"type": GeographicPoint, "distinctive_fields": ["ooi", "longitude", "latitude"]},
        # Monitoring
        "Application": {"type": Application, "distinctive_fields": Application._natural_key_attrs},
        "Incident": {"type": Incident, "distinctive_fields": Incident._natural_key_attrs},
        # Network
        "Network": {"type": Network, "default": "internet", "distinctive_fields": Network._natural_key_attrs},
        # ?baseclass :: referenced at IPPort, ResolvedHostname ... :: TypeFromRaw added
        "IPAddress": {"type": IPAddress, "distinctive_fields": IPAddress._natural_key_attrs},
        "IPAddressV4": {"type": IPAddressV4, "distinctive_fields": IPAddressV4._natural_key_attrs},
        "IPAddressV6": {"type": IPAddressV6, "distinctive_fields": IPAddressV6._natural_key_attrs},
        "IPPort": {"type": IPPort, "distinctive_fields": IPPort._natural_key_attrs},
        "AutonomousSystem": {"type": AutonomousSystem, "distinctive_fields": AutonomousSystem._natural_key_attrs},
        # ?baseclass :: referenced at DNSSPFMechanismNetBlock :: TypeFromRaw added
        "NetBlock": {"type": NetBlock, "distinctive_fields": NetBlock._natural_key_attrs},
        "IPV6NetBlock": {"type": IPV6NetBlock, "distinctive_fields": IPV6NetBlock._natural_key_attrs},
        "IPV4NetBlock": {"type": IPV4NetBlock, "distinctive_fields": IPV4NetBlock._natural_key_attrs},
        # Question
        "Question": {"type": Question, "distinctive_fields": Question._natural_key_attrs},
        # Reports
        "ReportData": {"type": ReportData, "distinctive_fields": ReportData._natural_key_attrs},
        "AssetReport": {"type": AssetReport, "distinctive_fields": AssetReport._natural_key_attrs},
        "Report": {"type": Report, "distinctive_fields": Report._natural_key_attrs},
        "HydratedReport": {"type": HydratedReport, "distinctive_fields": HydratedReport._natural_key_attrs},
        "ReportRecipe": {"type": ReportRecipe, "distinctive_fields": ReportRecipe._natural_key_attrs},
        # Scans
        "ExternalScan": {"type": ExternalScan, "distinctive_fields": ExternalScan._natural_key_attrs},
        # Service
        "Service": {"type": Service, "distinctive_fields": Service._natural_key_attrs},
        "IPService": {"type": IPService, "distinctive_fields": IPService._natural_key_attrs},
        "TLSCipher": {"type": TLSCipher, "distinctive_fields": TLSCipher._natural_key_attrs},
        # Software
        "Software": {"type": Software, "distinctive_fields": Software._natural_key_attrs},
        "SoftwareInstance": {"type": SoftwareInstance, "distinctive_fields": SoftwareInstance._natural_key_attrs},
        # Web
        "Website": {"type": Website, "distinctive_fields": Website._natural_key_attrs},
        # ?baseclass :: referenced at URL, RESTAPI ... :: need to initialize with proper class
        "WebURL": {"type": WebURL, "distinctive_fields": ["scheme", "port", "path"]},
        "HostnameHTTPURL": {"type": HostnameHTTPURL, "distinctive_fields": HostnameHTTPURL._natural_key_attrs},
        "IPAddressHTTPURL": {"type": IPAddressHTTPURL, "distinctive_fields": IPAddressHTTPURL._natural_key_attrs},
        "HTTPResource": {"type": HTTPResource, "distinctive_fields": HTTPResource._natural_key_attrs},
        "HTTPHeader": {"type": HTTPHeader, "distinctive_fields": HTTPHeader._natural_key_attrs},
        "URL": {"type": URL, "distinctive_fields": URL._natural_key_attrs},
        "HTTPHeaderURL": {"type": HTTPHeaderURL, "distinctive_fields": HTTPHeaderURL._natural_key_attrs},
        "HTTPHeaderHostname": {"type": HTTPHeaderHostname, "distinctive_fields": HTTPHeaderHostname._natural_key_attrs},
        "ImageMetadata": {"type": ImageMetadata, "distinctive_fields": ImageMetadata._natural_key_attrs},
        "RESTAPI": {"type": RESTAPI, "default": RESTAPI._natural_key_attrs},
        "APIDesignRule": {"type": APIDesignRule, "distinctive_fields": APIDesignRule._natural_key_attrs},
        "APIDesignRuleResult": {"type": APIDesignRuleResult, "distinctive_fields": APIDesignRuleResult._natural_key_attrs},
        "SecurityTXT": {"type": SecurityTXT, "distinctive_fields": SecurityTXT._natural_key_attrs},
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
        context['ooi_types'] = list(map(lambda x: _(x), self.ooi_types.keys()))
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

        # Controlling Shape of Data
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
        if hasattr(ooi_type, 'type_from_raw'): ooi_type = ooi_type.type_from_raw(ooi_dict)
        # check for cache
        if self.ooi_types[ooi_type.__name__].get('distinctive_fields'):
            field_name = self.get_cache_name(ooi_dict, self.ooi_types[ooi_type.__name__].get('distinctive_fields'))
            cache = self.reference_cache.setdefault(ooi_type.__name__, {})
            if field_name in cache:
                return cache[field_name]
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
        dins_field_comb = self.ooi_types[ooi_type.__name__].get('distinctive_fields')
        if dins_field_comb:
            cache = self.reference_cache.setdefault(ooi_type.__name__, {})
            field_name = self.get_cache_name(ooi_dict, dins_field_comb)
            cache[field_name] = ooi
        if ooi_dict.get("clearance") in CLEARANCE_VALUES:
            self.raise_clearance_level(ooi.reference, int(ooi_dict["clearance"]))
        return ooi

    def get_cache_name(self, ooi_dict:dict, field_combination: list[str]):
        """It creates name for cache from str values of distinctive fields"""
        return "|".join(filter(None, map(lambda a: str(ooi_dict.get(a, "")), field_combination)))

