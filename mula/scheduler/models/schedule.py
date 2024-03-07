import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from scheduler.utils import GUID, cron

from .base import Base
from .errors import ValidationError
from .queue import PrioritizedItem
from .tasks import Task, TaskRun


class Schedule(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    scheduler_id: str
    enabled: bool = True
    cron_expression: str | None = None
    task_id: uuid.UUID
    task: Task

    deadline_at: datetime | None = None
    evaluated_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # TODO: index on the p_item.hash

    def validate(self):
        """Validate the schedule model"""
        if self.cron_expression is not None:
            try:
                cron.next_run(self.cron_expression)
            except Exception as exc:
                raise ValidationError(f"Invalid cron expression: {self.cron_expression}") from exc


class ScheduleDB(Base):
    __tablename__ = "schedules"

    id = Column(GUID, primary_key=True)
    scheduler_id = Column(String)
    enabled = Column(Boolean, nullable=False, default=True)
    p_item = Column(JSONB, nullable=False)

    task_id = Column(GUID, ForeignKey("tasks.id"))
    task = relationship("TaskDB")

    cron_expression = Column(String, nullable=True)

    deadline_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    evaluated_at = Column(
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
