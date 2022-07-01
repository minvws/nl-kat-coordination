from __future__ import annotations

import string
from typing import Optional, Literal, Any

import dns
import dns.name
from pydantic import constr, validator

from octopoes.models import OOI, Reference
from octopoes.models.ooi.network import Network, IPAddress
from octopoes.models.persistence import ReferenceField

VALID_HOSTNAME_CHARACTERS = string.ascii_letters + string.digits + "-."


class DNSZone(OOI):
    object_type: Literal["DNSZone"] = "DNSZone"

    hostname: Reference = ReferenceField("Hostname", max_issue_scan_level=2, max_inherit_scan_level=0)
    parent: Optional[Reference] = ReferenceField(
        "DNSZone", max_issue_scan_level=0, max_inherit_scan_level=1, default=None
    )

    _natural_key_attrs = ["hostname"]

    _reverse_relation_names = {"parent": "child_dns_zones"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.hostname.name


class Hostname(OOI):
    object_type: Literal["Hostname"] = "Hostname"

    network: Reference = ReferenceField(Network)
    name: constr(to_lower=True)

    fqdn: Optional[Reference] = ReferenceField(
        "Hostname", max_issue_scan_level=4, max_inherit_scan_level=4, default=None
    )
    dns_zone: Optional[Reference] = ReferenceField(
        DNSZone, max_issue_scan_level=0, max_inherit_scan_level=2, default=None
    )

    _natural_key_attrs = ["network", "name"]

    _reverse_relation_names = {
        "network": "hostnames",
        "dns_zone": "hostnames",
        "fqdn": "fqdn_of",
    }

    @validator("name")
    def hostname_valid(cls, v: str) -> str:
        for c in v:
            if c not in VALID_HOSTNAME_CHARACTERS:
                raise ValueError(f"Invalid hostname character: {c}")

        if v.endswith("-"):
            raise ValueError("Hostname must not end with a hyphen")

        return v

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.name

    def __init__(self, **data: Any):
        super().__init__(**data)
        fqdn = str(dns.name.from_text(self.name))
        if fqdn == self.name:
            self.fqdn = self.reference
        else:
            self.fqdn = Hostname(network=self.network, name=fqdn).reference


class ResolvedHostname(OOI):
    object_type: Literal["ResolvedHostname"] = "ResolvedHostname"

    hostname: Reference = ReferenceField(Hostname, max_issue_scan_level=0, max_inherit_scan_level=4)
    address: Reference = ReferenceField(IPAddress, max_issue_scan_level=4, max_inherit_scan_level=0)

    _natural_key_attrs = ["hostname", "address"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"{reference.tokenized.hostname.name} -> {reference.tokenized.address.address}"


Hostname.update_forward_refs()
DNSZone.update_forward_refs()
