from enum import Enum
from functools import total_ordering
from typing import Annotated, Literal

from pydantic import AnyUrl, StringConstraints

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField

severity_order = [
    "unknown",
    "pending",
    "recommendation",
    "low",
    "medium",
    "high",
    "critical",
]


@total_ordering
class RiskLevelSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    RECOMMENDATION = "recommendation"

    # pending = KAT still has to run the boefje to determine the risk level
    PENDING = "pending"

    # unknown = the third party has been contacted, but third party has not determined the risk level (yet)
    UNKNOWN = "unknown"

    def __gt__(self, other: "RiskLevelSeverity") -> bool:
        return severity_order.index(self.value) > severity_order.index(other.value)

    def __str__(self):
        return self.value


class FindingType(OOI):
    id: str

    description: str | None = None
    source: AnyUrl | None = None
    impact: str | None = None
    recommendation: str | None = None

    risk_score: float | None = None
    risk_severity: RiskLevelSeverity | None = None

    _natural_key_attrs = ["id"]
    _traversable = False

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.id


class ADRFindingType(FindingType):
    object_type: Literal["ADRFindingType"] = "ADRFindingType"


class CVEFindingType(FindingType):
    object_type: Literal["CVEFindingType"] = "CVEFindingType"

    id: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True)]


class CWEFindingType(FindingType):
    object_type: Literal["CWEFindingType"] = "CWEFindingType"

    id: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True)]


class CAPECFindingType(FindingType):
    object_type: Literal["CAPECFindingType"] = "CAPECFindingType"

    id: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True)]


class RetireJSFindingType(FindingType):
    object_type: Literal["RetireJSFindingType"] = "RetireJSFindingType"


class SnykFindingType(FindingType):
    object_type: Literal["SnykFindingType"] = "SnykFindingType"

    id: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True)]


class KATFindingType(FindingType):
    object_type: Literal["KATFindingType"] = "KATFindingType"


class Finding(OOI):
    object_type: Literal["Finding"] = "Finding"

    finding_type: Reference = ReferenceField(FindingType)
    ooi: Reference = ReferenceField(OOI)
    proof: str | None = None
    description: str | None = None
    reproduce: str | None = None

    @property
    def natural_key(self) -> str:
        return f"{str(self.ooi)}|{self.finding_type.natural_key}"

    _reverse_relation_names = {"ooi": "findings", "finding_type": "instances"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        parts = reference.natural_key.split("|")
        finding_type = parts.pop()
        ooi_reference = Reference.from_str("|".join(parts))
        return f"{finding_type} @ {ooi_reference.human_readable}"


class MutedFinding(OOI):
    object_type: Literal["MutedFinding"] = "MutedFinding"

    finding: Reference = ReferenceField(Finding)
    reason: str | None = None

    _natural_key_attrs = ["finding"]
    _reverse_relation_names = {"finding": "mutes"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"Muted {reference.natural_key}"
