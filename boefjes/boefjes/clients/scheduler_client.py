import datetime
import uuid
from enum import Enum
from typing import Any

from httpx import Client, HTTPTransport, Response
from pydantic import BaseModel, TypeAdapter

from boefjes.config import settings
from boefjes.job_models import BoefjeMeta, NormalizerMeta


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
    schedule_id: uuid.UUID | None = None
    organisation: str
    priority: int
    status: TaskStatus
    type: str
    hash: str | None = None
    data: BoefjeMeta | NormalizerMeta
    created_at: datetime.datetime
    modified_at: datetime.datetime


class TaskPop(BaseModel):
    results: list[Task]


class SchedulerClientInterface:
    def get_queues(self) -> list[Queue]:
        raise NotImplementedError()

    def pop_item(self, scheduler_id: str) -> Task | None:
        raise NotImplementedError()

    def pop_items(self, scheduler_id: str, filters: dict[str, Any]) -> TaskPop | None:
        raise NotImplementedError()

    def patch_task(self, task_id: uuid.UUID, status: TaskStatus) -> None:
        raise NotImplementedError()

    def get_task(self, task_id: uuid.UUID) -> Task:
        raise NotImplementedError()

    def push_item(self, p_item: Task) -> None:
        raise NotImplementedError()


class SchedulerAPIClient(SchedulerClientInterface):
    def __init__(self, base_url: str):
        self._session = Client(
            base_url=base_url, transport=HTTPTransport(retries=6), timeout=settings.outgoing_request_timeout
        )

    @staticmethod
    def _verify_response(response: Response) -> None:
        response.raise_for_status()

    def pop_item(self, scheduler_id: str) -> Task | None:
        response = self._session.post(f"/schedulers/{scheduler_id}/pop?limit=1")
        self._verify_response(response)

        popped_tasks = TypeAdapter(TaskPop | None).validate_json(response.content)

        if len(popped_tasks.results) == 0:
            return None

        return popped_tasks.results[0]

    def pop_items(self, scheduler_id: str, filters: dict[str, Any]) -> TaskPop | None:
        response = self._session.post(f"/schedulers/{scheduler_id}/pop", json=filters)
        self._verify_response(response)

        return TypeAdapter(TaskPop | None).validate_json(response.content)

    def push_item(self, p_item: Task) -> None:
        response = self._session.post(f"/schedulers/{p_item.scheduler_id}/push", content=p_item.model_dump_json())
        self._verify_response(response)

    def patch_task(self, task_id: uuid.UUID, status: TaskStatus) -> None:
        response = self._session.patch(f"/tasks/{task_id}", json={"status": status.value})
        self._verify_response(response)

    def get_task(self, task_id: uuid.UUID) -> Task:
        response = self._session.get(f"/tasks/{task_id}")
        self._verify_response(response)

        return Task.model_validate_json(response.content)
