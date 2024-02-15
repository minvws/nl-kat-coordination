import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import AwareDatetime, BaseModel, Field

from octopoes.models import Reference
from octopoes.models.types import OOIType


class ServiceHealth(BaseModel):
    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = Field(default_factory=list)


ServiceHealth.model_rebuild()


class _BaseObservation(BaseModel):
    method: str
    source: Reference
    result: List[OOIType]
    valid_time: AwareDatetime
    task_id: uuid.UUID


# Connector models (more generic)
class Observation(_BaseObservation):
    """Used by Octopoes Connector to describe request body"""

    result: List[OOIType]
    valid_time: datetime


class Declaration(BaseModel):
    """Used by Octopoes Connector to describe request body"""

    ooi: OOIType
    valid_time: datetime
    method: Optional[str] = None
    task_id: Optional[uuid.UUID] = None


class Affirmation(BaseModel):
    """Used by Octopoes Connector to describe request body"""

    ooi: OOIType
    valid_time: datetime
    method: Optional[str] = None
    task_id: Optional[uuid.UUID] = None


class ScanProfileDeclaration(BaseModel):
    reference: Reference
    level: int
    valid_time: datetime


# API models (timezone validation and pydantic parsing)
class ValidatedObservation(_BaseObservation):
    """Used by Octopoes API to validate and parse correctly"""

    result: List[OOIType]
    valid_time: AwareDatetime


class ValidatedDeclaration(BaseModel):
    """Used by Octopoes API to validate and parse correctly"""

    ooi: OOIType
    valid_time: AwareDatetime
    method: Optional[str] = "manual"
    task_id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4())


class ValidatedAffirmation(BaseModel):
    """Used by Octopoes API to validate and parse correctly"""

    ooi: OOIType
    valid_time: AwareDatetime
    method: Optional[str] = "hydration"
    task_id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4)
