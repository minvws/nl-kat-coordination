import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from .base import Base


class SchedulerType(str, enum.Enum):
    """Enum for scheduler types."""

    BOEFJE = "boefje"
    NORMALIZER = "normalizer"
    REPORT = "report"


class Scheduler(BaseModel):
    id: str  # TODO: refactor to uuid?
    enabled: bool | None = None
    size: int | None = None
    maxsize: int | None = None
    organisation: str | None = None
    type: SchedulerType | None = None
    allow_replace: bool | None = None
    allow_updates: bool | None = None
    allow_priority_updates: bool | None = None

    last_activity: datetime | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None


class SchedulerDB(Base):
    __tablename__ = "schedulers"

    id = Column(String, primary_key=True)
    enabled = Column(Boolean, default=True)
    size = Column(Integer, nullable=False)
    maxsize = Column(Integer, nullable=False)
    organisation = Column(String, nullable=False)
    type = Column(String, nullable=False)
    allow_replace = Column(Boolean, default=True)
    allow_updates = Column(Boolean, default=True)
    allow_priority_updates = Column(Boolean, default=True)

    last_activity = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    modified_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
