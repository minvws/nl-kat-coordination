import datetime
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# A deliberate relative import to make this module self-contained
from .job_models import BoefjeMeta, NormalizerMeta


class JobRuntimeError(RuntimeError):
    """Base exception class for exceptions raised during running of jobs"""


class Queue(BaseModel):
    id: str
    size: int


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    id: uuid.UUID
    scheduler_id: str
    schedule_id: str | None
    organisation: str
    priority: int
    status: TaskStatus
    type: str
    hash: str | None = None
    data: BoefjeMeta | NormalizerMeta
    created_at: datetime.datetime
    modified_at: datetime.datetime


class StatusEnum(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class File(BaseModel):
    name: str | None = None
    content: str = Field(json_schema_extra={"contentEncoding": "base64"})
    tags: list[str] | None = None


class BoefjeOutput(BaseModel):
    status: StatusEnum
    files: list[File] | None = None


class Handler:
    def handle(self, task: Task) -> None:
        raise NotImplementedError()


class PaginatedTasksResponse(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[Task]


class SchedulerClientInterface:
    def pop_item(self, scheduler_id: str) -> Task | None:
        raise NotImplementedError()

    def pop_items(self, scheduler_id: str, filters: dict[str, Any]) -> PaginatedTasksResponse | None:
        raise NotImplementedError()

    def patch_task(self, task_id: uuid.UUID, status: TaskStatus) -> None:
        raise NotImplementedError()

    def get_task(self, task_id: uuid.UUID) -> Task:
        raise NotImplementedError()

    def push_item(self, p_item: Task) -> None:
        raise NotImplementedError()


class BoefjeStorageInterface:
    def save_raws(self, boefje_meta_id: uuid.UUID, boefje_output: BoefjeOutput) -> dict[str, uuid.UUID]:
        raise NotImplementedError()
