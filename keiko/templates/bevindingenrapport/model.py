"""
DNS Report Datamodel
"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from keiko.base_models import DataShapeBase


class OOI(BaseModel):
    id: Optional[str] = None
    ooi_type: Optional[str] = None
    human_readable: Optional[str] = None
    object_type: Optional[str] = None


class Finding(OOI):
    proof: Optional[str] = None
    description: Optional[str] = None
    reproduce: Optional[str] = None
    ooi: str


class FindingType(OOI):
    ooi_type: str

    risk: Optional[str] = None
    recommendation: Optional[str] = None

    cvss: Optional[str] = None
    source: Optional[str] = None
    information_updated: Optional[str] = Field(None, alias="information updated")

    risk_score: Optional[float] = None
    risk_severity: str = "pending"
    Information: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(coerce_numbers_to_str=True)


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
    report_url: Optional[str] = None
