import enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from .base import Base


class SchedulerType(str, enum.Enum):
    """Enum for scheduler types."""

    BOEFJE = "boefje"
    NORMALIZER = "normalizer"
    REPORT = "report"


class Scheduler(BaseModel):
    id: str
    enabled: bool | None = None
    maxsize: int | None = None
    organisation: str | None = None
    type: SchedulerType | None = None
    allow_replace: bool | None = None
    allow_updates: bool | None = None
    allow_priority_updates: bool | None = None

    last_activity: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SchedulerDB(Base):
    __tablename__ = "schedulers"

    id = Column(String, primary_key=True)
    enabled = Column(Boolean, default=True)
    maxsize = Column(Integer, nullable=False)
    organisation = Column(String, nullable=False)
    type = Column(Enum(SchedulerType), nullable=False)
    allow_replace = Column(Boolean, default=True)
    allow_updates = Column(Boolean, default=True)
    allow_priority_updates = Column(Boolean, default=True)

    last_activity = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    modified_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
