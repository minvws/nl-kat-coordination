import enum
import uuid

from pydantic import BaseModel, ConfigDict, Field

from .p_item import PrioritizedItem


class TaskStatus(enum.Enum):
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
    # Whether to populate models with the value property of enums, rather than
    # the raw enum. This may be useful if you want to serialise model.dict()
    # later (default: False). In this case the value property of the enum is
    # a string.
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID | None = None

    scheduler_id: str | None = None

    type: str | None = None

    p_item: PrioritizedItem | None = None

    status: TaskStatus | None = None
