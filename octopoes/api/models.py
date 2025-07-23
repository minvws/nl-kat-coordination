import uuid
from datetime import datetime

from pydantic import AwareDatetime, BaseModel

from octopoes.models import Reference
from octopoes.models.types import OOIType


class _BaseObservation(BaseModel):
    method: str
    source: Reference
    source_method: str | None
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
    end_valid_time: datetime | None = None
    method: str | None = None
    source_method: str | None = None
    task_id: uuid.UUID | None = None


class Affirmation(BaseModel):
    """Used by Octopoes Connector to describe request body"""

    ooi: OOIType
    valid_time: datetime
    method: str | None = None
    source_method: str | None = None
    task_id: uuid.UUID | None = None
