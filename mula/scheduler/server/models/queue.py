import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from scheduler.models import Task, TaskStatus


class Queue(BaseModel):
    id: str
    size: int
    maxsize: int
    item_type: str
    allow_replace: bool
    allow_updates: bool
    allow_priority_updates: bool
    pq: list[Task] | None = None


class TaskPush(BaseModel):
    id: uuid.UUID | None = None
    scheduler_id: str | None = None
    schedule_id: uuid.UUID | None = None
    priority: int | None = None
    status: TaskStatus | None = None
    type: str | None = None
    hash: str | None = None
    data: dict | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
