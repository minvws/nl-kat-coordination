from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Schedule(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hash: str | None = Field(None, max_length=32)

    data: dict | None = {}

    enabled: bool | None = True

    schedule: str | None = None

    deadline_at: datetime | None = None
