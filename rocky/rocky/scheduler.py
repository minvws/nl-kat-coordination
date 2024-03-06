from __future__ import annotations

import datetime
import json
import uuid
from enum import Enum
from http import HTTPStatus
from logging import getLogger
from typing import Any

import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny
from requests.exceptions import HTTPError

from rocky.health import ServiceHealth

logger = getLogger(__name__)


class Boefje(BaseModel):
    """Boefje representation."""

    id: str
    name: str | None = Field(default=None)
    version: str | None = Field(default=None)


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: uuid.UUID
    boefje: Boefje
    input_ooi: str | None = None
    arguments: dict[str, Any]
    organization: str
    started_at: datetime.datetime | None = None
    ended_at: datetime.datetime | None = None


class RawData(BaseModel):
    id: uuid.UUID
    boefje_meta: BoefjeMeta
    mime_types: list[dict[str, str]]
    secure_hash: str | None = None
    hash_retrieval_link: str | None = None


class Normalizer(BaseModel):
    """Normalizer representation."""

    id: str | None = None
    name: str | None = None
    version: str | None = Field(default=None)


class NormalizerMeta(BaseModel):
    id: uuid.UUID
    raw_data: RawData
    normalizer: Normalizer
    started_at: datetime.datetime
    ended_at: datetime.datetime


class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    id: uuid.UUID | None = None
    normalizer: Normalizer
    raw_data: RawData
    type: str = "normalizer"


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    id: uuid.UUID | None = None
    boefje: Boefje
    input_ooi: str | None = None
    organization: str
    type: str = "boefje"


class PrioritizedItem(BaseModel):
    """Representation of a queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue prioritized items to a JSON
    representation.
    """

    id: uuid.UUID | None = None
    hash: str | None = None
    priority: int
    data: SerializeAsAny[BoefjeTask | NormalizerTask]


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: uuid.UUID | None = None
    scheduler_id: str
    type: str
    p_item: PrioritizedItem
    status: TaskStatus
    created_at: datetime.datetime
    modified_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)


class SchedulerError(Exception):
    message = _("Connectivity issues with Mula.")

    def __str__(self):
        return str(self.message)


class TooManyRequestsError(SchedulerError):
    message = _("Task queue is full, please try again later.")


class BadRequestError(SchedulerError):
    message = _("Task is invalid.")


class ConflictError(SchedulerError):
    message = _("Task already queued.")


class TaskNotFoundError(SchedulerError):
    message = _("Task not found.")


class SchedulerClient:
    def __init__(self, base_uri: str):
        self.session = requests.Session()
        self._base_uri = base_uri

    def list_tasks(self, **kwargs) -> dict[str, Any]:
        response = self.session.get(f"{self._base_uri}/tasks", params=kwargs)
        response.raise_for_status()
        return response.json()

    def get_task_details(self, organization_code: str, task_id: str) -> Task:
        res = self.session.get(f"{self._base_uri}/tasks/{task_id}")
        res.raise_for_status()
        task_details = Task.model_validate_json(res.content)

        if task_details.type == "normalizer":
            organization = task_details.p_item.data.raw_data.boefje_meta.organization
        else:
            organization = task_details.p_item.data.organization

        if organization != organization_code:
            raise TaskNotFoundError()
        return task_details

    def push_task(self, queue_name: str, prioritized_item: PrioritizedItem) -> None:
        try:
            res = self.session.post(f"{self._base_uri}/queues/{queue_name}/push", data=prioritized_item.json())
            res.raise_for_status()
        except HTTPError as http_error:
            code = http_error.response.status_code
            if code == HTTPStatus.TOO_MANY_REQUESTS:
                raise TooManyRequestsError()
            elif code == HTTPStatus.BAD_REQUEST:
                raise BadRequestError()
            elif code == HTTPStatus.CONFLICT:
                raise ConflictError()
            else:
                raise SchedulerError()

    def health(self) -> ServiceHealth:
        health_endpoint = self.session.get(f"{self._base_uri}/health")
        health_endpoint.raise_for_status()
        return ServiceHealth.model_validate_json(health_endpoint.content)

    def get_task_stats(self, organization_code: str, task_type: str) -> dict:
        try:
            res = self.session.get(f"{self._base_uri}/tasks/stats/{task_type}-{organization_code}")
            res.raise_for_status()
        except HTTPError:
            raise SchedulerError()
        task_stats = json.loads(res.content)
        return task_stats


client = SchedulerClient(settings.SCHEDULER_API)


class PaginatedTasksResponse(BaseModel):
    count: int = 0
    results: list[Task] = []
    pages: list[int] = []


class SchedulerPagintor:
    client: SchedulerClient = SchedulerClient(settings.SCHEDULER_API)

    def __init__(self, scheduler_id: str, limit: int = 0):
        self.scheduler_id: str = scheduler_id
        self.limit: int = limit

    def get_page_objects(self, page_number: int = 1, **kwargs) -> PaginatedTasksResponse:
        if self.limit == 0:
            tasks = SchedulerPagintor.client.list_tasks(scheduler_id=self.scheduler_id, offset=0, **kwargs)
        else:
            offset = (page_number * self.limit) - self.limit

            tasks = SchedulerPagintor.client.list_tasks(
                scheduler_id=self.scheduler_id, limit=self.limit, offset=offset, **kwargs
            )
        task_list_details = {
            "count": tasks["count"],
            "results": tasks["results"],
            "pages": self.get_page_numbers(tasks["count"]),
        }

        return PaginatedTasksResponse(**task_list_details)

    def get_page_numbers(self, total_objects) -> list[int] | None:
        if self.limit > 0 and self.limit < total_objects:
            total_pages = int(total_objects / self.limit)
            if total_objects % self.limit != 0:
                total_pages += 1
            return [i for i in range(1, total_pages + 1)]
        return []
