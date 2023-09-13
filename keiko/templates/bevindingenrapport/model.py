"""
DNS Report Datamodel
"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from keiko.base_models import DataShapeBase


class OOI(BaseModel):
    id: Optional[str]
    ooi_type: Optional[str]
    human_readable: Optional[str]
    object_type: Optional[str]


class Finding(OOI):
    proof: Optional[str]
    description: Optional[str]
    reproduce: Optional[str]
    ooi: str


class FindingType(OOI):
    ooi_type: str

    risk: Optional[str]
    recommendation: Optional[str]

    cvss: Optional[str]
    source: Optional[str]
    information_updated: Optional[str] = Field(None, alias="information updated")

    risk_score: Optional[float]
    risk_severity: str = "pending"
    Information: Optional[str]
    description: Optional[str]


class FindingOccurrence(BaseModel):
    finding_type: FindingType
    list: List[Finding]


class Meta(BaseModel):
    total: int
    total_by_severity: Dict[str, int]
    total_by_finding_type: Dict[str, int]
    total_finding_types: int
    total_by_severity_per_finding_type: Dict[str, int]


class DataShape(DataShapeBase):
    meta: Meta
    findings_grouped: Dict[str, FindingOccurrence]
    valid_time: datetime
    report_source_type: str
    report_source_value: str
    filters: dict
    report_url: Optional[str]
