from datetime import datetime
from typing import Optional, Any, List

from pydantic import BaseModel

from octopoes.models import Reference, OOI
from octopoes.models.datetime import TimezoneAwareDatetime
from octopoes.models.types import OOIType


class ServiceHealth(BaseModel):
    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = []


ServiceHealth.update_forward_refs()


class _BaseObservation(BaseModel):
    method: str
    source: Reference
    result: List[OOIType]
    valid_time: TimezoneAwareDatetime
    task_id: str


# Connector models (more generic)
class Observation(_BaseObservation):
    """Used by Octopoes Connector to describe request body"""

    result: List[OOI]
    valid_time: datetime


class Declaration(BaseModel):
    """Used by Octopoes Connector to describe request body"""

    ooi: OOI
    valid_time: datetime


class ScanProfileDeclaration(BaseModel):
    reference: Reference
    level: int
    valid_time: datetime


# API models (timezone validation and pydantic parsing)
class ValidatedObservation(_BaseObservation):
    """Used by Octopoes API to validate and parse correctly"""

    result: List[OOIType]
    valid_time: TimezoneAwareDatetime


class ValidatedDeclaration(BaseModel):
    """Used by Octopoes API to validate and parse correctly"""

    ooi: OOIType
    valid_time: TimezoneAwareDatetime
