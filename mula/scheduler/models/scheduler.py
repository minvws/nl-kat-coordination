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
    enabled: bool = True
    maxsize: int
    organisation: str
    type: SchedulerType
    allow_replace: bool = True
    allow_updates: bool = True
    allow_priority_updates: bool = True

    last_activity: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SchedulerDB(Base):
    __tablename__ = "schedulers"

    id = Column(String, primary_key=True)
    enabled = Column(Boolean, default=True, nullable=False)
    maxsize = Column(Integer, nullable=False)
    organisation = Column(String, nullable=False)
    type = Column(SQLAlchemyEnum(SchedulerType), nullable=False)
    allow_replace = Column(Boolean, default=True, nullable=False)
    allow_updates = Column(Boolean, default=True, nullable=False)
    allow_priority_updates = Column(Boolean, default=True)

    last_activity = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    modified_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
