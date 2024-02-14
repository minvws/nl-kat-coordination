import uuid
from datetime import datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field

from octopoes.models import Reference
from octopoes.models.types import OOIType


class ServiceHealth(BaseModel):
    service: str
    healthy: bool = False
    version: str | None = None
    additional: Any = None
    results: list["ServiceHealth"] = Field(default_factory=list)


ServiceHealth.model_rebuild()


class _BaseObservation(BaseModel):
    method: str
    source: Reference
    result: list[OOIType]
    valid_time: AwareDatetime
    task_id: uuid.UUID


# Connector models (more generic)
class Observation(_BaseObservation):
    """Used by Octopoes Connector to describe request body"""

    result: list[OOIType]
    valid_time: datetime


class Declaration(BaseModel):
    """Used by Octopoes Connector to describe request body"""

    ooi: OOIType
    valid_time: datetime
    method: str | None = None
    task_id: uuid.UUID | None = None


class ScanProfileDeclaration(BaseModel):
    reference: Reference
    level: int
    valid_time: datetime


# API models (timezone validation and pydantic parsing)
class ValidatedObservation(_BaseObservation):
    """Used by Octopoes API to validate and parse correctly"""

    result: list[OOIType]
    valid_time: AwareDatetime


class ValidatedDeclaration(BaseModel):
    """Used by Octopoes API to validate and parse correctly"""

    ooi: OOIType
    valid_time: AwareDatetime
    method: str | None = "manual"
    task_id: uuid.UUID | None = Field(default_factory=lambda: uuid.uuid4())
