from __future__ import annotations

import datetime
import json
import uuid
from enum import Enum
from functools import cached_property
from logging import getLogger
from typing import Any

import httpx
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from httpx import ConnectError, HTTPError, HTTPStatusError, RequestError, codes
from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny, ValidationError

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


class PaginatedTasksResponse(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[Task]


class LazyTaskList:
    HARD_LIMIT = 99_999_999

    def __init__(
        self,
        scheduler_client: SchedulerClient,
        **kwargs,
    ):
        self.scheduler_client = scheduler_client
        self.kwargs = kwargs
        self._count: int | None = None

    @cached_property
    def count(self) -> int:
        if self._count is None:
            self._count = self.scheduler_client.list_tasks(
                limit=0,
                **self.kwargs,
            ).count
        return self._count

    def __len__(self):
        return self.count

    def __getitem__(self, key) -> list[Task]:
        if isinstance(key, slice):
            offset = key.start or 0
            limit = LazyTaskList.HARD_LIMIT
            if key.stop:
                limit = key.stop - offset
        elif isinstance(key, int):
            offset = key
            limit = 1
        else:
            raise TypeError("Invalid slice argument type.")

        res = self.scheduler_client.list_tasks(
            limit=limit,
            offset=offset,
            **self.kwargs,
        )

        self._count = res.count
        return res.results


class SchedulerError(Exception):
    message = _("Could not connect to Scheduler. Service is possibly down.")

    def __init__(self, *args: object, message: str | None = None) -> None:
        super().__init__(*args)
        if message is not None:
            self.message = message

    def __str__(self):
        return str(self.message)


class SchedulerClient:
    def __init__(self, base_uri: str, organization_code: str):
        self._client = httpx.Client(base_url=base_uri)
        self.organization_code = organization_code

    def list_tasks(
        self,
        **kwargs,
    ) -> PaginatedTasksResponse:
        try:
            kwargs = {k: v for k, v in kwargs.items() if v is not None}  # filter Nones from kwargs
            res = self._client.get("/tasks", params=kwargs)
            return PaginatedTasksResponse.model_validate_json(res.content)
        except ValidationError:
            raise SchedulerError(_("Your request could not be validated."))
        except ConnectError:
            raise SchedulerError()

    def get_task_details(self, task_id: str) -> Task:
        try:
            res = self._client.get(f"/tasks/{task_id}")
            res.raise_for_status()
            task_details = Task.model_validate_json(res.content)

            if task_details.type == "normalizer":
                organization = task_details.p_item.data.raw_data.boefje_meta.organization
            else:
                organization = task_details.p_item.data.organization

            if organization != self.organization_code:
                raise SchedulerError(_("Task not found."))

            return task_details
        except (HTTPStatusError, ConnectError):
            raise SchedulerError()

    def push_task(self, prioritized_item: PrioritizedItem) -> None:
        try:
            queue_name = f"{prioritized_item.data.type}-{self.organization_code}"
            res = self._client.post(
                f"/queues/{queue_name}/push",
                content=prioritized_item.json(),
                headers={"Content-Type": "application/json"},
            )
            res.raise_for_status()
        except HTTPStatusError as http_error:
            code = http_error.response.status_code
            if code == codes.TOO_MANY_REQUESTS:
                raise SchedulerError(_("{}: Task queue is full, please try again later.").format(code))
            elif code == codes.BAD_REQUEST:
                raise SchedulerError(_("{}: Bad request").format(code))
            elif code == codes.CONFLICT:
                raise SchedulerError(_("{}: Task already queued.").format(code))
        except RequestError:
            raise SchedulerError()

    def health(self) -> ServiceHealth:
        try:
            health_endpoint = self._client.get("/health")
            health_endpoint.raise_for_status()
            return ServiceHealth.model_validate_json(health_endpoint.content)
        except ConnectError:
            raise SchedulerError()

    def get_task_stats(self, organization_code: str, task_type: str) -> dict:
        try:
            res = self._client.get(f"/tasks/stats/{task_type}-{organization_code}")
            res.raise_for_status()
        except (ConnectError, HTTPError):
            raise SchedulerError()
        task_stats = json.loads(res.content)
        return task_stats


def scheduler_client(organization_code: str) -> SchedulerClient:
    return SchedulerClient(settings.SCHEDULER_API, organization_code)
