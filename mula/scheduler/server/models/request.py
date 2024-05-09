import enum
import uuid

from pydantic import BaseModel, ConfigDict, Field


class PrioritizedItem(BaseModel):
    """Request model for prioritized items used in the server."""

    priority: int
    data: dict = Field(default_factory=dict)


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
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None

    scheduler_id: str | None = None

    type: str | None = None

    p_item: PrioritizedItem | None = None

    status: TaskStatus | None = None
