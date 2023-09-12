import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from octopoes.models import OOI, Reference
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
    task_id: uuid.UUID


# Connector models (more generic)
class Observation(_BaseObservation):
    """Used by Octopoes Connector to describe request body"""

    result: List[OOI]
    valid_time: datetime


class Declaration(BaseModel):
    """Used by Octopoes Connector to describe request body"""

    ooi: OOI
    valid_time: datetime
    method: Optional[str]
    task_id: Optional[uuid.UUID]


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
    method: Optional[str] = "manual"
    task_id: Optional[uuid.UUID] = Field(default_factory=lambda: uuid.uuid4())
