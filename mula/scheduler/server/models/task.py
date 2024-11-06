import uuid
from datetime import datetime

from pydantic import BaseModel

from scheduler.models import TaskStatus


class Task(BaseModel):
    id: uuid.UUID
    scheduler_id: str
    schedule_id: uuid.UUID | None
    priority: int | None
    status: TaskStatus | None
    type: str
    hash: str | None
    data: dict | None
    created_at: datetime
    modified_at: datetime


class TaskUpdate(BaseModel):
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
