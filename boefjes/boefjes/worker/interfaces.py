import datetime
import uuid
from enum import Enum

from pydantic import BaseModel

from boefjes.job_models import BoefjeMeta, NormalizerMeta


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
    def handle(self, task: Task):
        raise NotImplementedError()


class BoefjeJobRunner:
    def run(self, boefje_meta: BoefjeMeta, environment: dict[str, str]) -> list[tuple[set, bytes | str]]:
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
