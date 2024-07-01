import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID | None = None

    scheduler_id: str | None = None

    schedule_id: uuid.UUID | None = None

    priority: int | None = 0

    status: TaskStatus = TaskStatus.PENDING

    hash: str | None = None

    data: dict | None = None

    created_at: datetime | None = None
    modified_at: datetime | None = None
