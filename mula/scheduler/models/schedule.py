import uuid
from datetime import datetime, timezone
from typing import List, Optional

import mmh3
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text

from scheduler.utils import GUID, cron

from .base import Base
from .errors import ValidationError
from .queue import PrioritizedItem
from .tasks import TaskRun


class Schedule(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    scheduler_id: str

    enabled: bool = True

    # Priority item specification
    p_item: PrioritizedItem

    tasks: List[TaskRun] = []

    cron_expression: Optional[str] = None

    deadline_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None
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
    tasks = relationship(
        "TaskRunDB", back_populates="schedule", order_by="TaskRunDB.created_at", cascade="all,delete-orphan"
    )
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
