import datetime
import uuid
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# A deliberate relative import to make this module self-contained
from .job_models import BoefjeMeta, NormalizerMeta


class JobRuntimeError(RuntimeError):
    """Base exception class for exceptions raised during running of jobs"""


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
    schedule_id: str | None
    organization: str
    priority: int
    status: TaskStatus
    type: str
    data: BoefjeMeta | NormalizerMeta
    created_at: datetime.datetime
    modified_at: datetime.datetime

    @classmethod
    def from_db(cls, task) -> "Task":  # type: ignore
        return cls(
            id=task.id,
            schedule_id=task.schedule_id,
            organization=task.organization.code,
            priority=task.priority,
            status=task.status,
            type=task.type,
            data=task.data,
            created_at=task.created_at,
            modified_at=task.modified_at,
        )


class StatusEnum(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class File(BaseModel):
    name: str
    content: str = Field(json_schema_extra={"contentEncoding": "base64"})
    type: str


class BoefjeInput(BaseModel):
    output_url: str
    task: Task
    model_config = ConfigDict(extra="forbid")


class BoefjeOutput(BaseModel):
    status: StatusEnum
    files: list[File] = Field(default_factory=list)


class BoefjeHandler:
    def handle(self, task: Task) -> tuple[dict, BoefjeOutput]:
        raise NotImplementedError()


class NormalizerHandlerInterface:
    def handle(self, task: Task) -> None:
        raise NotImplementedError()


class BoefjeStorageInterface:
    def save_output(self, boefje_meta: BoefjeMeta, boefje_output: BoefjeOutput) -> dict[str, uuid.UUID]:
        raise NotImplementedError()
