import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from scheduler.utils import GUID, cron

from .base import Base
from .task import Task


class Schedule(BaseModel):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    scheduler_id: str

    hash: str | None = Field(None, max_length=32)

    data: dict | None = None

    enabled: bool = True

    schedule: str | None = None

    tasks: list[Task] = []

    _deadline_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, **data):
        super().__init__(**data)

        if "deadline_at" in data:
            self.deadline_at = data["deadline_at"]
        elif "deadline_at" not in data and self.schedule is not None:
            self.deadline_at = cron.next_run(self.schedule)

    @computed_field  # type: ignore
    @property
    def deadline_at(self) -> datetime | None:
        """Two ways to calculate the deadline_at:
        1. If the self._deadline_at is already set, return it.
        2. If the schedule is set, calculate the next run and return it.
        """
        if self._deadline_at is not None:
            return self._deadline_at

        if self.schedule is not None:
            return cron.next_run(self.schedule)

        return None

    @deadline_at.setter
    def deadline_at(self, value: datetime | None):
        self._deadline_at = value

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, value: str) -> str:
        """Custom validation for the schedule cron expression."""
        if value is None:
            return value

        try:
            cron.next_run(value)
            return value
        except Exception as exc:
            raise ValueError(f"Invalid cron expression: {value}") from exc

    @classmethod
    def model_validate(cls, data):
        """By default when creating an instance with model_validate() will not
        set the deadline_at when using computed_fields. This method will set
        the deadline_at if it is passed in the data."""
        instance = super().model_validate(data)
        if hasattr(data, "deadline_at"):
            instance.deadline_at = getattr(data, "deadline_at")
        return instance


class ScheduleDB(Base):
    __tablename__ = "schedules"

    id = Column(GUID, primary_key=True)

    scheduler_id = Column(String, nullable=False)

    hash = Column(String(32), nullable=True, unique=True)

    data = Column(JSONB, nullable=False)

    enabled = Column(Boolean, nullable=False, default=True)

    schedule = Column(String, nullable=True)

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
