from __future__ import annotations

from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Literal

from pydantic import Field

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class Network(OOI):
    object_type: Literal["Network"] = "Network"

    name: str

    _natural_key_attrs = ["name"]
    _traversable = False

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.name


class IPAddress(OOI):
    address: IPv4Address | IPv6Address
    network: Reference = ReferenceField(Network)

    _natural_key_attrs = ["network", "address"]
    _information_value = ["address"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.address


class IPAddressV4(IPAddress):
    object_type: Literal["IPAddressV4"] = "IPAddressV4"
    address: IPv4Address

    netblock: Reference | None = ReferenceField(
        "IPV4NetBlock", optional=True, max_issue_scan_level=0, max_inherit_scan_level=4, default=None
    )

    _reverse_relation_names = {"network": "ip_v4_addresses", "netblock": "ip_v4_addresses"}


class IPAddressV6(IPAddress):
    object_type: Literal["IPAddressV6"] = "IPAddressV6"
    address: IPv6Address

    netblock: Reference | None = ReferenceField(
        "IPV6NetBlock", optional=True, max_issue_scan_level=0, max_inherit_scan_level=4, default=None
    )

    _reverse_relation_names = {"network": "ip_v6_addresses", "netblock": "ip_v6_addresses"}


class Protocol(Enum):
    TCP = "tcp"
    UDP = "udp"


class PortState(Enum):
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNFILTERED = "unfiltered"
    OPEN_FILTERED = "open|filtered"
    CLOSED_FILTERED = "closed|filtered"


class IPPort(OOI):
    object_type: Literal["IPPort"] = "IPPort"

    address: Reference = ReferenceField(IPAddress, max_issue_scan_level=0, max_inherit_scan_level=4)
    protocol: Protocol
    port: Annotated[int, Field(gt=0, lt=2**16)]
    state: PortState | None = None

    _natural_key_attrs = ["address", "protocol", "port"]
    _reverse_relation_names = {"address": "ports"}
    _information_value = ["protocol", "port"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        tokenized = reference.tokenized
        return f"{tokenized.address.address}:{tokenized.port}/{tokenized.protocol}"


class AutonomousSystem(OOI):
    object_type: Literal["AutonomousSystem"] = "AutonomousSystem"

    number: str
    name: str | None
    _natural_key_attrs = ["number"]


class NetBlock(OOI):
    network: Reference = ReferenceField(Network)

    name: str | None = None
    description: str | None = None

    announced_by: Reference | None = ReferenceField(AutonomousSystem, default=None)
    parent: Reference | None = ReferenceField("NetBlock", default=None)

    _natural_key_attrs = ["network", "start_ip", "mask"]

    _reverse_relation_names = {"announced_by": "announced_netblocks", "parent": "child_netblocks"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"{reference.tokenized.start_ip.address}/{reference.tokenized.mask}"


class IPV6NetBlock(NetBlock):
    object_type: Literal["IPV6NetBlock"] = "IPV6NetBlock"

    parent: Reference | None = ReferenceField("IPV6NetBlock", default=None)

    start_ip: Reference = ReferenceField(IPAddressV6, max_issue_scan_level=4)
    mask: Annotated[int, Field(ge=0, lt=128)]

    _reverse_relation_names = {"parent": "child_netblocks", "announced_by": "announced_ipv6_netblocks"}


class IPV4NetBlock(NetBlock):
    object_type: Literal["IPV4NetBlock"] = "IPV4NetBlock"

    parent: Reference | None = ReferenceField("IPV4NetBlock", default=None)

    start_ip: Reference = ReferenceField(IPAddressV4, max_issue_scan_level=4)
    mask: Annotated[int, Field(ge=0, lt=32)]

    _reverse_relation_names = {"parent": "child_netblocks", "announced_by": "announced_ipv4_netblocks"}


IPAddressV4.model_rebuild()
IPAddressV6.model_rebuild()
NetBlock.model_rebuild()
IPV4NetBlock.model_rebuild()
IPV6NetBlock.model_rebuild()
