import datetime
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from scheduler.utils import GUID

from .base import Base
from .queue import PrioritizedItem
from .tasks import Task


class Job(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    scheduler_id: uuid.UUID
    hash: str
    enabled: bool = True
    crontab: Optional[str]

    p_item: PrioritizedItem
    tasks: List[Task] = []

    deadline: Optional[datetime.datetime] = None

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    modified_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        orm_mode = True


class JobORM(Base):
    __tablename__ = "jobs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    scheduler_id = Column(String)
    hash = Column(String(32), index=True)
    enabled = Column(Boolean, default=True)
    crontab = Column(String)

    p_item = Column(JSONB, nullable=False)
    tasks = relationship("TaskORM", back_populates="job")

    deadline = Column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
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
