import datetime
import uuid
from enum import Enum

from pydantic import BaseModel

# A deliberate relative import to make this module (more) self-contained
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
    priority: int
    status: TaskStatus
    type: str
    hash: str | None = None
    data: BoefjeMeta | NormalizerMeta
    created_at: datetime.datetime
    modified_at: datetime.datetime


class Handler:
    def handle(self, task: Task) -> None:
        raise NotImplementedError()


class SchedulerClientInterface:
    def get_queues(self) -> list[Queue]:
        raise NotImplementedError()

    def pop_item(self, queue_id: str) -> Task | None:
        raise NotImplementedError()

    def patch_task(self, task_id: uuid.UUID, status: TaskStatus) -> None:
        raise NotImplementedError()

    def get_task(self, task_id: uuid.UUID) -> Task:
        raise NotImplementedError()

    def push_item(self, p_item: Task) -> None:
        raise NotImplementedError()


class BoefjeStorageInterface:
    def save_boefje_meta(self, boefje_meta: BoefjeMeta) -> None:
        raise NotImplementedError()

    def save_raw(self, boefje_meta_id: uuid.UUID, raw: str | bytes, mime_types: set[str] = frozenset()) -> uuid.UUID:
        raise NotImplementedError()
