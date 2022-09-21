from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, Literal

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.web import Website
from octopoes.models.persistence import ReferenceField


class AlgorithmType(Enum):
    RSA = "RSA"
    ECC = "ECC"


class Certificate(OOI):
    object_type: Literal["Certificate"] = "Certificate"

    subject: str
    issuer: str
    valid_from: str
    valid_until: str
    pk_algorithm: str
    pk_size: int
    pk_number: str

    website: Reference = ReferenceField(Website, max_issue_scan_level=0, max_inherit_scan_level=1)
    signed_by: Optional[Reference] = ReferenceField(
        "Certificate", max_issue_scan_level=1, max_inherit_scan_level=0, default=None
    )

    _natural_key_attrs = ["website", "subject", "issuer"]

    @property
    def expired(self):
        return datetime.now() > datetime.fromisoformat(self.valid_until)

    _reverse_relation_names = {
        "website": "certificates",
        "signed_by": "signed_certificates",
    }

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"{reference.tokenized.subject} ({reference.tokenized.issuer})"


class CertificateSubjectAlternativeName(OOI):
    object_type: Literal["CertificateSubjectAlternativeName"] = "CertificateSubjectAlternativeName"

    certificate: Reference = ReferenceField(Certificate, max_issue_scan_level=0, max_inherit_scan_level=1)
    hostname: Reference = ReferenceField(Hostname, max_issue_scan_level=1, max_inherit_scan_level=0)

    _natural_key_attrs = ["certificate", "hostname"]

    _reverse_relation_names = {"certificate": "subject_alternative_names", "hostname": "certificates"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"{reference.tokenized.certificate.subject} ({reference.tokenized.certificate.issuer}) contains {reference.tokenized.hostname.name}"


Certificate.update_forward_refs()
CertificateSubjectAlternativeName.update_forward_refs()
