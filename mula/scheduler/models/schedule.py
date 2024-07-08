import uuid
from datetime import datetime, timezone
from typing import ClassVar

import mmh3
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text

from scheduler.utils import GUID, cron

from .base import Base
from .errors import ValidationError
from .task import Task


class Schedule(BaseModel):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    scheduler_id: str

    hash: str | None = Field(None, max_length=32)

    data: dict | None = {}

    enabled: bool = True

    schedule: str | None = None

    tasks: list[Task] = []

    deadline_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, value: str) -> str:
        """Validate the schedule cron expression."""
        if value is None:
            return value

        try:
            cron.next_run(value)
            return value
        except Exception as exc:
            raise ValueError(f"Invalid cron expression: {value}") from exc


class ScheduleDB(Base):
    __tablename__ = "schedules"

    id = Column(GUID, primary_key=True)

    scheduler_id = Column(String, nullable=False)

    hash = Column(String(32), nullable=True)  # TODO: unique=True

    data = Column(JSONB, nullable=False)

    enabled = Column(Boolean, nullable=False, default=True)

    schedule = Column(String, nullable=True)

    # TODO: cascade
    tasks = relationship("TaskDB", back_populates="schedule")

    deadline_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
