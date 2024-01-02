import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from scheduler.utils import GUID

from .base import Base
from .queue import PrioritizedItem
from .tasks import Task


class Job(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    scheduler_id: str

    enabled: bool

    p_item: PrioritizedItem

    tasks: List[Task] = []

    deadline_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None
    created_at = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobDB(Base):
    __tablename__ = "jobs"

    id = Column(GUID, primary_key=True)
    schedler_id = Column(String)
    enabled = Column(Boolean, nullable=False, default=True)
    p_item = Column(JSONB, nullable=False)
    tasks = relationship("TaskDB", backref="job", lazy="dynamic")

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
        opupdate=func.now(),
    )
