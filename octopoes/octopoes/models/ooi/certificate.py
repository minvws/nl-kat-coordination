from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Literal, Optional

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddress
from octopoes.models.persistence import ReferenceField


class AlgorithmType(Enum):
    RSA = "RSA"
    ECC = "ECC"


class X509Certificate(OOI):
    object_type: Literal["X509Certificate"] = "X509Certificate"

    subject: Optional[str] = None
    issuer: Optional[str] = None
    valid_from: str
    valid_until: str
    pk_algorithm: Optional[str] = None
    pk_size: Optional[int] = None
    pk_number: Optional[str] = None
    signed_by: Optional[Reference] = ReferenceField(
        "X509Certificate", max_issue_scan_level=1, max_inherit_scan_level=0, default=None
    )
    serial_number: str
    expires_in: Optional[timedelta] = None

    _natural_key_attrs = ["issuer", "serial_number"]

    @property
    def expired(self):
        return datetime.now() > datetime.fromisoformat(self.valid_until)

    _reverse_relation_names = {
        "signed_by": "signed_certificates",
    }

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"{reference.tokenized.issuer} ({reference.tokenized.serial_number})"


class SubjectAlternativeName(OOI):
    certificate: Reference = ReferenceField(X509Certificate)

    _natural_key_attrs = ["certificate"]


class SubjectAlternativeNameHostname(SubjectAlternativeName):
    object_type: Literal["SubjectAlternativeNameHostname"] = "SubjectAlternativeNameHostname"
    hostname: Reference = ReferenceField(Hostname, max_issue_scan_level=1, max_inherit_scan_level=0)

    _natural_key_attrs = ["certificate", "hostname"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.hostname.name


class SubjectAlternativeNameIP(SubjectAlternativeName):
    object_type: Literal["SubjectAlternativeNameIP"] = "SubjectAlternativeNameIP"
    address: Reference = ReferenceField(IPAddress)

    _natural_key_attrs = ["certificate", "address"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.address.address


class SubjectAlternativeNameQualifier(SubjectAlternativeName):
    object_type: Literal["SubjectAlternativeNameQualifier"] = "SubjectAlternativeNameQualifier"
    name: str

    _natural_key_attrs = ["certificate", "name"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.name


X509Certificate.model_rebuild()
SubjectAlternativeNameHostname.model_rebuild()
SubjectAlternativeNameIP.model_rebuild()
SubjectAlternativeNameQualifier.model_rebuild()
