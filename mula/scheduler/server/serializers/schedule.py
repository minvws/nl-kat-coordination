from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scheduler_id: str
    organisation: str
    data: dict
    schedule: str | None = None
    deadline_at: datetime | None = None


# NOTE: model added for support of partial updates
class SchedulePatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hash: str | None = Field(None, max_length=32)
    data: dict | None = None
    enabled: bool | None = None
    schedule: str | None = None
    deadline_at: datetime | None = None
