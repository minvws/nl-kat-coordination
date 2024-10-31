import datetime
import json
import uuid
from enum import Enum
from typing import Any

from httpx import Client, HTTPTransport, Response
from pydantic import BaseModel, TypeAdapter

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
    schedule_id: str | None
    priority: int
    status: TaskStatus
    type: str
    hash: str | None = None
    data: BoefjeMeta | NormalizerMeta
    created_at: datetime.datetime
    modified_at: datetime.datetime


class Filter(BaseModel):
    column: str
    field: str
    operator: str
    value: Any


class QueuePopRequest(BaseModel):
    filters: list[Filter]


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


class SchedulerAPIClient(SchedulerClientInterface):
    def __init__(
        self, base_url: str, task_capabilities: list[str] | None = None, reachable_networks: list[str] | None = None
    ):
        self._session = Client(base_url=base_url, transport=HTTPTransport(retries=6))
        self._task_capabilities = task_capabilities
        self._reachable_networks = reachable_networks

    @staticmethod
    def _verify_response(response: Response) -> None:
        response.raise_for_status()

    def get_queues(self) -> list[Queue]:
        response = self._session.get("/queues")
        self._verify_response(response)

        return TypeAdapter(list[Queue]).validate_json(response.content)

    def pop_item(self, queue_id: str) -> Task | None:
        filters: list[Filter] = []

        # Client should only pop tasks that lie on a network that the runner is capable of reaching (e.g. the internet)
        if self._reachable_networks:
            filters.append(
                Filter(column="data", field="network", operator="<@", value=json.dumps(self._reachable_networks))
            )

        # Client should only pop tasks that have requirements that this runner is capable of (e.g. being able
        # to handle ipv6 requests)
        if self._task_capabilities:
            filters.append(
                Filter(column="data", field="requirements", operator="<@", value=json.dumps(self._task_capabilities))
            )

        response = self._session.post(
            f"/queues/{queue_id}/pop", data=QueuePopRequest(filters=filters).model_dump_json()
        )
        self._verify_response(response)

        return TypeAdapter(Task | None).validate_json(response.content)

    def push_item(self, p_item: Task) -> None:
        response = self._session.post(f"/queues/{p_item.scheduler_id}/push", content=p_item.model_dump_json())
        self._verify_response(response)

    def patch_task(self, task_id: uuid.UUID, status: TaskStatus) -> None:
        response = self._session.patch(f"/tasks/{task_id}", json={"status": status.value})
        self._verify_response(response)

    def get_task(self, task_id: uuid.UUID) -> Task:
        response = self._session.get(f"/tasks/{task_id}")
        self._verify_response(response)

        return Task.model_validate_json(response.content)
