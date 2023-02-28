from __future__ import annotations

from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import Union, Optional, Literal

from pydantic.types import conint

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class MockNetwork(OOI):
    object_type: Literal["MockNetwork"] = "MockNetwork"
    name: str
    _natural_key_attrs = ["name"]


class MockIPAddress(OOI):
    address: Union[IPv4Address, IPv6Address]
    network: Reference = ReferenceField(MockNetwork)

    _natural_key_attrs = ["network", "address"]
    _reverse_relation_names = {
        "network": "ip_addresses",
    }


class MockIPAddressV4(MockIPAddress):
    object_type: Literal["MockIPAddressV4"] = "MockIPAddressV4"
    address: IPv4Address

    _reverse_relation_names = {
        "network": "ip_v4_addresses",
    }


class MockIPAddressV6(MockIPAddress):
    object_type: Literal["MockIPAddressV6"] = "MockIPAddressV6"
    address: IPv6Address

    _reverse_relation_names = {
        "network": "ip_v6_addresses",
    }


class MockProtocol(Enum):
    TCP = "tcp"
    UDP = "udp"


class MockPortState(Enum):
    OPEN = "open"
    CLOSED = "closed"


class MockDNSZone(OOI):
    object_type: Literal["MockDNSZone"] = "MockDNSZone"
    hostname: Reference = ReferenceField("MockHostname", max_inherit_scan_level=2)

    _natural_key_attrs = ["hostname"]
    _reverse_relation_names = {
        "hostname": "dns_zone",
    }


class MockIPPort(OOI):
    object_type: Literal["MockIPPort"] = "MockIPPort"

    address: Reference = ReferenceField(MockIPAddress, max_issue_scan_level=0, max_inherit_scan_level=4)
    protocol: MockProtocol
    port: conint(gt=0, lt=2**16)
    state: Optional[MockPortState]

    _natural_key_attrs = ["address", "protocol", "port"]
    _reverse_relation_names = {
        "address": "ports",
    }


class MockIPService(OOI):
    object_type: Literal["MockIPService"] = "MockIPService"

    ip_port: Reference = ReferenceField(MockIPPort, max_issue_scan_level=0, max_inherit_scan_level=4)
    service: str

    _natural_key_attrs = ["ip_port", "service"]
    _reverse_relation_names = {
        "ip_port": "ip_services",
    }


class MockHostname(OOI):
    object_type: Literal["MockHostname"] = "MockHostname"

    dns_zone: Optional[Reference] = ReferenceField(MockDNSZone, default=None, max_issue_scan_level=1)
    network: Reference = ReferenceField(MockNetwork)
    name: str
    fqdn: Optional[Reference] = ReferenceField("MockHostname", default=None)

    _natural_key_attrs = ["network", "name"]
    _reverse_relation_names = {
        "network": "hostnames",
        "dns_zone": "hostnames",
        "fqdn": "fqdn_of",
    }


class MockResolvedHostname(OOI):
    object_type: Literal["MockResolvedHostname"] = "MockResolvedHostname"

    # hostname -> address: 4
    # address -> hostname: 0
    hostname: Reference = ReferenceField(MockHostname, max_issue_scan_level=0, max_inherit_scan_level=4)
    address: Reference = ReferenceField(MockIPAddress, max_issue_scan_level=4, max_inherit_scan_level=0)

    _natural_key_attrs = ["hostname", "address"]
    _reverse_relation_names = {
        "hostname": "resolved_hostnames",
        "address": "resolved_hostnames",
    }


class MockDNSCNAMERecord(OOI):
    object_type: Literal["MockDNSCNAMERecord"] = "MockDNSCNAMERecord"

    hostname: Reference = ReferenceField(MockHostname)
    value: str
    target_hostname: Reference = ReferenceField(MockHostname)

    _natural_key_attrs = ["hostname", "value"]
    _reverse_relation_names = {
        "hostname": "dns_cname_records",
        "target_hostname": "dns_cname_record_targets",
    }


class MockLabel(OOI):
    object_type: Literal["MockLabel"] = "MockLabel"

    ooi: Reference = ReferenceField(OOI)
    label_id: str
    label_text: Optional[str]

    @property
    def natural_key(self) -> str:
        return f"{self.ooi}|{self.label_id}"

    _reverse_relation_names = {
        "ooi": "labels",
    }


ALL_OOI_TYPES = {
    OOI,
    MockNetwork,
    MockIPAddress,
    MockIPAddressV4,
    MockIPAddressV6,
    MockIPPort,
    MockHostname,
    MockDNSZone,
    MockResolvedHostname,
    MockDNSCNAMERecord,
}

for ooi_type in ALL_OOI_TYPES:
    ooi_type.update_forward_refs()
