from typing import Literal

from octopoes.models import OOI, Reference
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.web import WebURL
from octopoes.models.persistence import ReferenceField


class ExternalScan(OOI):
    object_type: Literal["ExternalScan"] = "ExternalScan"

    name: str

    _natural_key_attrs = ["name"]
    _information_value = ["name"]
    _traversable = False

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.name


class SSDPResponse(OOI):
    """OOI holding information about a found response from SSDP. Example response https://wiki.wireshark.org/SSDP"""

    object_type: Literal["SSDPService"] = "SSDPService"

    _natural_key_attrs = ["network", "server", "usn"]

    web_url: Reference | None = ReferenceField(WebURL, default=None)
    network: Reference = ReferenceField(Network)

    nt: str
    nts: str
    server: str
    usn: str
