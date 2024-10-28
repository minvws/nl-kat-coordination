import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskStatus(str, enum.Enum):
    # Task has been created but not yet queued
    PENDING = "pending"

    # Task has been pushed onto queue and is ready to be picked up
    QUEUED = "queued"

    # Task has been picked up by a worker
    DISPATCHED = "dispatched"

    # Task has been picked up by a worker, and the worker indicates that it is
    # running.
    RUNNING = "running"

    # Task has been completed
    COMPLETED = "completed"

    # Task has failed
    FAILED = "failed"

    # Task has been cancelled
    CANCELLED = "cancelled"


class TaskDetail(BaseModel):
    id: uuid.UUID
    scheduler_id: str | None
    schedule_id: uuid.UUID | None
    priority: int | None
    status: TaskStatus | None
    type: str | None
    hash: str | None
    data: dict | None
    created_at: datetime
    modified_at: datetime


class TaskCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    # TODO: check if these all need to be nullable
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


class TaskPatch(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

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
