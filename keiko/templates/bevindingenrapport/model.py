"""
DNS Report Datamodel
"""
from datetime import datetime
from typing import Dict, List, Optional, Union, Literal

from pydantic import BaseModel, Field

from keiko.base_models import DataShapeBase


class OOI(BaseModel):
    id: str
    ooi_type: str
    human_readable: str
    object_type: str


class Finding(OOI):
    proof: Optional[str]
    description: str
    reproduce: Optional[str]
    ooi: str


class FindingTypeBase(OOI):
    risk_level_source: Optional[str]
    risk_level_score: float
    risk_level_severity: str
    Information: Optional[str]
    description: Optional[str]


class KATFindingType(FindingTypeBase):
    ooi_type: Literal["KATFindingType"]
    risk: Optional[str]
    recommendation: Optional[str]


class CVEFindingType(FindingTypeBase):
    ooi_type: Literal["CVEFindingType"]
    cvss: str
    source: str
    information_updated: Optional[str] = Field(..., alias="information updated")


class RetireJSFindingType(FindingTypeBase):
    ooi_type: Literal["RetireJSFindingType"]
    source: str
    information_updated: Optional[str] = Field(..., alias="information updated")


FindingType = Union[KATFindingType, CVEFindingType, RetireJSFindingType]


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
