import enum
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Integer, String
from sqlalchemy.sql import func

from .base import Base


class SchedulerType(str, enum.Enum):
    """Enum for scheduler types."""

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
