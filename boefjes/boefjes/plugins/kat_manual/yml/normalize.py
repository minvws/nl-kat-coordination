import yaml
import io
import logging
from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from boefjes.job_models import NormalizerDeclaration, NormalizerOutput
from octopoes.models import OOI, Reference
from octopoes.models.types import OOIType
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.dns.records import NXDOMAIN, DNSAAAARecord, DNSARecord, DNSCAARecord, \
    DNSCNAMERecord, DNSMXRecord, DNSNSRecord, DNSPTRRecord, DNSRecord, DNSSOARecord, DNSTXTRecord
from octopoes.models.ooi.email_security import DKIMExists, DKIMKey, DKIMSelector, DMARCTXTRecord, \
    DNSSPFMechanism, DNSSPFMechanismHostname, DNSSPFMechanismIP, DNSSPFMechanismNetBlock, DNSSPFRecord
from models.ooi.findings import FindingType, ADRFindingType, CVEFindingType, CWEFindingType, \
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

OOI_TYPES: dict[str, dict] = {
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

logger = logging.getLogger(__name__)


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    reference_cache = {"Network": {"internet": Network(name="internet")}}

    yield from process_yml(raw, reference_cache)


def process_yml(yml_raw_data: bytes, reference_cache: dict) -> Iterable[NormalizerOutput]:
    yml_data = io.StringIO(yml_raw_data.decode("UTF-8"))
    oois_from_yaml = yaml.safe_load(yml_data)
    oois = []
    for ooi_number, ooi_dict in enumerate(oois_from_yaml, start=1):
        try:
            create_oois(ooi_dict, reference_cache, oois)
        except ValidationError as err:
            logger.exception("Validation failed for indexed object at %s", ooi_number)
            logger.exception(f"with error: {str(err)}")
    
    return oois

def create_oois(ooi_dict:dict, reference_cache:dict, oois_list:list, ooi_type=None):
    # constants
    skip_properties = ("object_type", "scan_profile", "primary_key", "user_id")
    # check for main ooi
    if ooi_type == None:
        main_ooi_type, main_dict = tuple(ooi_dict.items())[0]
        ooi_dict = main_dict
        if main_ooi_type not in OOI_TYPES:
            raise ValueError('The main level ooi type not found. Also the main level ooi name is case sensitive.')
        ooi_type = OOI_TYPES[main_ooi_type]["type"]
    # Special Cases
    if hasattr(ooi_type, 'type_from_raw'): ooi_type = ooi_type.type_from_raw(ooi_dict)
    # check for cache
    if OOI_TYPES[ooi_type.__name__].get('distinctive_fields'):
        field_name = get_cache_name(ooi_dict, OOI_TYPES[ooi_type.__name__].get('distinctive_fields'))
        cache = reference_cache.setdefault(ooi_type.__name__, {})
        if ooi_dict[field_name] in cache:
            return cache[ooi_dict[field_name]]
    # creation process
    ooi_fields = [
        (field, field if model_field.annotation != Reference else model_field.json_schema_extra['object_type'], model_field.annotation == Reference, model_field.is_required())
        for field, model_field in ooi_type.__fields__.items()
        if field not in skip_properties
    ]
    kwargs: dict[str, Any] = {}
    for field, referenced_type, is_reference, required in ooi_fields:
        # required referenced fields or not required but also defined in yaml
        if is_reference and required or is_reference and ooi_dict.get(field):
            try:
                referenced_ooi = create_oois(
                    ooi_dict.get(field.lower()) or ooi_dict.get(referenced_type.lower()),
                    reference_cache,
                    oois_list,
                    OOI_TYPES[referenced_type]['type'],
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
    dins_field_comb = OOI_TYPES[ooi_type.__name__].get('distinctive_fields')
    if dins_field_comb:
        field_name = get_cache_name(ooi_dict, dins_field_comb)
        cache = reference_cache.setdefault(ooi_type.__name__, {})
        cache[ooi_dict[field_name]] = ooi
    oois_list.append(NormalizerDeclaration(ooi=ooi))
    return ooi

def get_cache_name(ooi_dict:dict, field_combination: list[str]):
    """It creates name for cache from str values of distinctive fields"""
    return "|".join(filter(None, map(lambda a: str(ooi_dict.get(a, "")), field_combination)))
