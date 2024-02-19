"""
DNS Report Datamodel
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from keiko.base_models import DataShapeBase


class OOI(BaseModel):
    id: str | None = None
    ooi_type: str | None = None
    human_readable: str | None = None
    object_type: str | None = None


class Finding(OOI):
    proof: str | None = None
    description: str | None = None
    reproduce: str | None = None
    ooi: str


class FindingType(OOI):
    ooi_type: str

    risk: str | None = None
    recommendation: str | None = None

    cvss: str | None = None
    source: str | None = None
    information_updated: str | None = Field(None, alias="information updated")

    risk_score: float | None = None
    risk_severity: str = "pending"
    Information: str | None = None
    description: str | None = None

    model_config = ConfigDict(coerce_numbers_to_str=True)


class FindingOccurrence(BaseModel):
    finding_type: FindingType
    list: list[Finding]


class Meta(BaseModel):
    total: int
    total_by_severity: dict[str, int]
    total_by_finding_type: dict[str, int]
    total_finding_types: int
    total_by_severity_per_finding_type: dict[str, int]


class DataShape(DataShapeBase):
    meta: Meta
    findings_grouped: dict[str, FindingOccurrence]
    valid_time: datetime
    report_source_type: str
    report_source_value: str
    filters: dict
    report_url: str | None = None
