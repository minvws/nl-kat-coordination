import yaml
import io
import logging
from collections.abc import Iterable
from typing import Any, TypedDict, NotRequired

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

class OOITypeEntry(TypedDict):
    type: Any
    distinctive_fields: NotRequired[list[str]]

OOI_TYPES: dict[str, OOITypeEntry] = {
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

def get_distinctive_fields(ooi_type):
    return OOI_TYPES[ooi_type.__name__].get('distinctive_fields', ooi_type._natural_key_attrs)

def create_oois(ooi_dict:dict, reference_cache:dict, oois_list:list):
    # constants
    skip_properties = ("object_type", "scan_profile", "primary_key", "user_id")
    # check for main ooi
    ooi_type = OOI_TYPES[ooi_dict["ooi_type"]]["type"]
    # Special Cases
    if hasattr(ooi_type, 'type_from_raw'): ooi_type = ooi_type.type_from_raw(ooi_dict)
    # check for cache
    cache, cache_field_name = get_cache_and_field_name(ooi_type, ooi_dict, reference_cache)
    if cache_field_name in cache: return cache[cache_field_name]
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
                    oois_list
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
    oois_list.append(NormalizerDeclaration(ooi=ooi))
    return ooi
    
def get_cache_and_field_name(ooi_type, ooi_dict: dict, reference_cache:dict):
    dins_fields = get_distinctive_fields(ooi_type)
    cache_field_name = get_cache_name(ooi_dict, dins_fields)
    cache = reference_cache.setdefault(ooi_type.__name__, {})
    return cache, cache_field_name

def get_cache_name(ooi_dict:dict, field_combination: list[str]):
    """It creates name for cache from str values of distinctive fields"""
    return "|".join(filter(None, map(lambda a: str(ooi_dict.get(a, "")), field_combination)))
