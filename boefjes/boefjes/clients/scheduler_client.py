import datetime
import logging
import uuid
from enum import Enum

from httpx import Client, HTTPTransport, Response
from pydantic import BaseModel, TypeAdapter

from boefjes.job_models import BoefjeMeta, NormalizerMeta

logger = logging.getLogger(__name__)


class Queue(BaseModel):
    id: str
    size: int


class QueuePrioritizedItem(BaseModel):
    """Representation of a queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue prioritized items to a JSON
    representation.
    """

    id: uuid.UUID
    priority: int
    hash: str | None = None
    data: BoefjeMeta | NormalizerMeta


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: uuid.UUID
    scheduler_id: str
    type: str
    p_item: QueuePrioritizedItem
    status: TaskStatus
    created_at: datetime.datetime
    modified_at: datetime.datetime


class Filter(BaseModel):
    column: str
    field: str
    operator: str
    value: list[str]


class QueuePopRequest(BaseModel):
    filters: list[Filter]


class SchedulerClientInterface:
    def get_queues(self) -> list[Queue]:
        raise NotImplementedError()

    def pop_item(self, queue: str, network_scopes: list[str]) -> QueuePrioritizedItem | None:
        """Pops item from `queue` with the corresponding `network_scopes`

        Args:
            queue (str): the name of the queue to pop from
            network_scopes (list[str]): A list of all scopes that the queue must pop from


        Returns:
            QueuePrioritizedItem | None
        """
        raise NotImplementedError()

    def patch_task(self, task_id: uuid.UUID, status: TaskStatus) -> None:
        raise NotImplementedError()

    def get_task(self, task_id: uuid.UUID) -> Task:
        raise NotImplementedError()

    def push_item(self, queue_id: str, p_item: QueuePrioritizedItem) -> None:
        raise NotImplementedError()


class SchedulerAPIClient(SchedulerClientInterface):
    def __init__(self, base_url: str):
        self._session = Client(base_url=base_url, transport=HTTPTransport(retries=6))

    @staticmethod
    def _verify_response(response: Response) -> None:
        response.raise_for_status()

    def get_queues(self) -> list[Queue]:
        response = self._session.get("/queues")
        self._verify_response(response)

        return TypeAdapter(list[Queue]).validate_json(response.content)

    def pop_item(self, queue: str, network_scopes: list[str]) -> QueuePrioritizedItem | None:
        response = self._session.post(
            f"/queues/{queue}/pop",
            data=QueuePopRequest(
                filters=[
                    Filter(
                        column="data",
                        field="network_scope",
                        operator="in",
                        value=network_scopes,
                    )
                ]
            ).model_dump_json(),
        )
        self._verify_response(response)

        return TypeAdapter(QueuePrioritizedItem | None).validate_json(response.content)

    def push_item(self, queue_id: str, p_item: QueuePrioritizedItem) -> None:
        response = self._session.post(f"/queues/{queue_id}/push", content=p_item.json())
        self._verify_response(response)

    def patch_task(self, task_id: uuid.UUID, status: TaskStatus) -> None:
        response = self._session.patch(f"/tasks/{task_id}", json={"status": status.value})
        self._verify_response(response)

    def get_task(self, task_id: uuid.UUID) -> Task:
        response = self._session.get(f"/tasks/{task_id}")
        self._verify_response(response)

        return Task.model_validate_json(response.content)
