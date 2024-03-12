import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text

from scheduler.utils import GUID

from .base import Base
from .tasks import Task, TaskStatus


class TaskRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    scheduler_id: str

    type: str

    task: Task
    task_id: uuid.UUID

    status: TaskStatus

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"Task(id={self.id}, scheduler_id={self.scheduler_id}, type={self.type}, status={self.status})"


class TaskRunDB(Base):
    __tablename__ = "task_runs"

    id = Column(GUID, primary_key=True)

    scheduler_id = Column(String)

    type = Column(String)

    # FIXME: ondelete
    task_id = Column(GUID, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=False)
    task = relationship("TaskDB", back_populates="task_runs")

    status = Column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDING,
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
