import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Schedule(BaseModel):
    id: uuid.UUID
    scheduler_id: str
    hash: str
    data: dict | None
    enabled: bool
    schedule: str | None
    deadline_at: datetime | None
    created_at: datetime
    modified_at: datetime


class ScheduleCreate(BaseModel):
    scheduler_id: str
    data: dict
    schedule: str
    deadline_at: datetime | None = None


# NOTE: model added for support of partial updates
class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hash: str | None = Field(None, max_length=32)

    data: dict | None = None

    enabled: bool | None = None

    schedule: str | None = None

    deadline_at: datetime | None = None
