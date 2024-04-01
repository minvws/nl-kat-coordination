import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from scheduler.utils import GUID

from .base import Base
from .task import Task, TaskDB


class PrioritizedItem(BaseModel):
    """Representation of an queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue prioritized items to a JSON
    representation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    scheduler_id: str | None = None

    # A unique generated identifier for the object contained in data
    hash: str | None = Field(None, max_length=32)

    priority: int | None = 0

    data: dict | None = {}

    task_id: uuid.UUID
    task: Task

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PrioritizedItemDB(Base):
    __tablename__ = "p_items"

    id = Column(GUID, primary_key=True)

    scheduler_id = Column(String)

    # TODO: rename to task_hash? or remove and get it through the task?
    hash = Column(String(32), index=True)

    priority = Column(Integer)

    data = Column(JSONB, nullable=False)

    task_id = Column(GUID, ForeignKey("tasks.id"))
    task = relationship("TaskDB", back_populates="p_item")

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

    def __init__(self, **kwargs):
        # NOTE: Fix for pydantic models (with nested objects) to sqlalchemy models.
        self.task = TaskDB(**kwargs.pop("task"))
        super().__init__(**kwargs)


class Queue(BaseModel):
    id: str
    size: int
    maxsize: int
    item_type: str
    allow_replace: bool
    allow_updates: bool
    allow_priority_updates: bool
    pq: list[PrioritizedItem] | None = None
