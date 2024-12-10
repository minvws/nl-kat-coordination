import enum
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class SchedulerType(str, enum.Enum):
    """Enum for scheduler types."""

    UNKNOWN = "unknown"
    BOEFJE = "boefje"
    NORMALIZER = "normalizer"
    REPORT = "report"


class Scheduler(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    type: SchedulerType
    last_activity: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
