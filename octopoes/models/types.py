from __future__ import annotations

from typing import Type, Dict, Set, Iterator, Union

from pydantic.fields import ModelField

from octopoes.models import OOI, Reference
from octopoes.models.ooi.certificate import Certificate
from octopoes.models.ooi.dns.records import (
    DNSARecord,
    DNSAAAARecord,
    DNSMXRecord,
    DNSTXTRecord,
    DNSNSRecord,
    DNSSOARecord,
    DNSCNAMERecord,
    DNSSPFMechanismIP,
    DNSSPFMechanismHostname,
    DNSSPFMechanismNetBlock,
    DNSSPFRecord,
    NXDOMAIN,
)
from octopoes.models.ooi.dns.zone import Hostname, DNSZone, ResolvedHostname
from octopoes.models.ooi.findings import (
    Finding,
    KATFindingType,
    CVEFindingType,
    CWEFindingType,
    RetireJSFindingType,
    SnykFindingType,
)
from octopoes.models.ooi.network import (
    Network,
    IPAddressV4,
    IPAddressV6,
    IPPort,
    AutonomousSystem,
    IPV4NetBlock,
    IPV6NetBlock,
)
from octopoes.models.ooi.service import Service, IPService
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.ooi.web import (
    Website,
    HostnameHTTPURL,
    IPAddressHTTPURL,
    HTTPResource,
    HTTPHeader,
    URL,
    HTTPHeaderURL,
    HTTPHeaderHostname,
)

CertificateType = Union[Certificate]
DnsType = Union[DNSZone, Hostname]
DnsRecordType = Union[
    DNSARecord,
    DNSAAAARecord,
    DNSTXTRecord,
    DNSMXRecord,
    DNSNSRecord,
    DNSSOARecord,
    DNSCNAMERecord,
    ResolvedHostname,
    NXDOMAIN,
]
FindingType = Union[
    Finding,
    KATFindingType,
    CVEFindingType,
    RetireJSFindingType,
    CWEFindingType,
    SnykFindingType,
]
NetworkType = Union[
    Network,
    IPAddressV4,
    IPAddressV6,
    AutonomousSystem,
    IPV4NetBlock,
    IPV6NetBlock,
    IPPort,
]
ServiceType = Union[Service, IPService]
SoftwareType = Union[Software, SoftwareInstance]
WebType = Union[
    Website, URL, HostnameHTTPURL, IPAddressHTTPURL, HTTPResource, HTTPHeader, HTTPHeaderURL, HTTPHeaderHostname
]

OOIType = Union[
    CertificateType,
    DnsType,
    DnsRecordType,
    FindingType,
    NetworkType,
    ServiceType,
    SoftwareType,
    WebType,
    DNSSPFMechanismIP,
    DNSSPFMechanismHostname,
    DNSSPFMechanismNetBlock,
    DNSSPFRecord,
]


def get_all_types(cls_: Type[OOI]) -> Iterator[Type[OOI]]:
    yield cls_
    for subcls in cls_.__subclasses__():
        yield from get_all_types(subcls)


ALL_TYPES = set(get_all_types(OOI))


def get_abstract_types() -> Set[Type[OOI]]:
    return {t for t in ALL_TYPES if t.__subclasses__()}


def get_concrete_types() -> Set[Type[OOI]]:
    return {t for t in ALL_TYPES if not t.__subclasses__()}


def get_collapsed_types() -> Set[Type[OOI]]:
    abstract_ooi_subtypes = get_abstract_types() - {OOI}

    subclasses_of_abstract_ooi: Set[Type[OOI]] = set()

    for concrete_type in get_concrete_types():
        for abstract_type in abstract_ooi_subtypes:
            if issubclass(concrete_type, abstract_type):
                subclasses_of_abstract_ooi.add(concrete_type)

    non_abstracted_concrete_types = get_concrete_types() - subclasses_of_abstract_ooi

    return abstract_ooi_subtypes.union(non_abstracted_concrete_types)


def to_concrete(object_types: Set[Type[OOI]]) -> Set[Type[OOI]]:
    concrete_types = set()
    for object_type in object_types:
        if object_type in get_concrete_types():
            concrete_types.add(object_type)
        else:
            child_concrete_types = {t for t in get_concrete_types() if issubclass(t, object_type)}
            concrete_types = concrete_types.union(child_concrete_types)
    return concrete_types


def type_by_name(type_name: str):
    return next(t for t in ALL_TYPES if t.__name__ == type_name)


def related_object_type(field: ModelField) -> Type[OOI]:
    object_type: Union[str, Type[OOI]] = field.field_info.extra["object_type"]
    if isinstance(object_type, str):
        return type_by_name(object_type)
    return object_type


def get_relations(object_type: Type[OOI]) -> Dict[str, Type[OOI]]:
    return {
        name: related_object_type(field) for name, field in object_type.__fields__.items() if field.type_ == Reference
    }


def get_relation(object_type: Type[OOI], property_name: str) -> Type[OOI]:
    return get_relations(object_type)[property_name]


# FIXME: legacy imports
OOI_TYPES = {ooi_type.get_object_type(): ooi_type for ooi_type in get_concrete_types()}
