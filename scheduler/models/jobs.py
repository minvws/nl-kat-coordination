import datetime
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from scheduler.utils import GUID

from .base import Base
from .queue import PrioritizedItem
from .tasks import Task


class ScheduledJob(BaseModel):
    id: uuid.UUID
    hash: str
    enabled: bool
    crontab: Optional[str]
    scheduler_id: str
    p_item: PrioritizedItem
    tasks: List[Task] = []

    next_check: Optional[datetime.datetime] = None

    checked_at: Optional[datetime.datetime] = None

    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow)

    modified_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow)

    class Config:
        orm_mode = True


class ScheduledJobORM(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    hash = Column(String, nullable=False)  # TODO: unique
    enabled = Column(Boolean, nullable=False)
    crontab = Column(String, nullable=True)
    scheduler_id = Column(String, nullable=False)
    p_item = Column(JSON, nullable=False)
    tasks = relationship("TaskORM", back_populates="scheduled_job")

    checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    modified_at = Column(DateTime, nullable=False)
