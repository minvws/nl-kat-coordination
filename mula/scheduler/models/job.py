import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, constr
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from scheduler.utils import GUID, cron

from .base import Base
from .queue import PrioritizedItem
from .rate_limit import RateLimit
from .tasks import Task


class Job(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    scheduler_id: str

    enabled: bool = True

    # Priority item specification
    p_item: PrioritizedItem

    tasks: List[Task] = []

    # TODO: not yet implemented, added as proof of concept
    rate_limit: Optional[RateLimit] = None

    cron_expression: Optional[str] = None

    deadline_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # TODO: index on the p_item.hash

    def validate(self):
        """Validate the job model"""
        if self.cron_expression is not None:
            try:
                cron.next_run(self.cron_expression)
            except Exception as exc:
                raise ValueError(f"Invalid cron expression: {self.cron_expression}") from exc


class JobDB(Base):
    __tablename__ = "jobs"

    id = Column(GUID, primary_key=True)
    scheduler_id = Column(String)
    enabled = Column(Boolean, nullable=False, default=True)
    p_item = Column(JSONB, nullable=False)
    tasks = relationship("TaskDB", back_populates="job", order_by="TaskDB.created_at", cascade="all,delete-orphan")
    rate_limit = Column(JSONB, nullable=True)
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
