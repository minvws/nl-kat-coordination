from __future__ import annotations

import datetime
import json
import uuid
from enum import Enum
from functools import cached_property
from http import HTTPStatus
from logging import getLogger
from typing import Any, Dict, List, Optional, Union

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
    name: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: uuid.UUID
    boefje: Boefje
    input_ooi: Optional[str] = None
    arguments: Dict[str, Any]
    organization: str
    started_at: Optional[datetime.datetime] = None
    ended_at: Optional[datetime.datetime] = None


class RawData(BaseModel):
    id: uuid.UUID
    boefje_meta: BoefjeMeta
    mime_types: List[Dict[str, str]]
    secure_hash: Optional[str] = None
    hash_retrieval_link: Optional[str] = None


class Normalizer(BaseModel):
    """Normalizer representation."""

    id: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = Field(default=None)


class NormalizerMeta(BaseModel):
    id: uuid.UUID
    raw_data: RawData
    normalizer: Normalizer
    started_at: datetime.datetime
    ended_at: datetime.datetime


class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    id: Optional[uuid.UUID] = None
    normalizer: Normalizer
    raw_data: RawData
    type: str = "normalizer"


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    id: Optional[uuid.UUID] = None
    boefje: Boefje
    input_ooi: Optional[str] = None
    organization: str
    type: str = "boefje"


class PrioritizedItem(BaseModel):
    """Representation of a queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue prioritized items to a JSON
    representation.
    """

    id: Optional[uuid.UUID] = None
    hash: Optional[str] = None
    priority: int
    data: SerializeAsAny[Union[BoefjeTask, NormalizerTask]]


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: Optional[uuid.UUID] = None
    scheduler_id: str
    type: str
    p_item: PrioritizedItem
    status: TaskStatus
    created_at: datetime.datetime
    modified_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedTasksResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[Task]


class SchedulerTaskList:
    HARD_LIMIT = 99_999_999

    def __init__(
        self,
        scheduler_client: SchedulerClient,
        **kwargs,
    ):
        self.scheduler_client = scheduler_client
        self.kwargs = kwargs
        self._count = 0

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

    def __getitem__(self, key: Union[int, slice]) -> List[Task]:
        if isinstance(key, slice):
            offset = key.start or 0
            limit = SchedulerTaskList.HARD_LIMIT
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

    def __str__(self):
        return str(self.message)


class TooManyRequestsError(SchedulerError):
    message = _("Task queue is full, please try again later.")


class BadRequestError(SchedulerError):
    message = _("Task is invalid.")


class ConflictError(SchedulerError):
    message = _("Task already queued.")


class TaskNotFoundError(SchedulerError):
    message = _("Task could not be found.")


class SchedulerClient:
    def __init__(self, base_uri: str, organization_code: str):
        self._base_uri = base_uri
        self.organization_code = organization_code
        self.session = requests.Session()

    def list_tasks(self, **kwargs) -> PaginatedTasksResponse:
        res = self.session.get(f"{self._base_uri}/tasks", params=kwargs)
        return PaginatedTasksResponse.model_validate_json(res.content)

    def get_task_details(self, task_id: str) -> Optional[Task]:
        res = self.session.get(f"{self._base_uri}/tasks/{task_id}")
        res.raise_for_status()
        task_details = Task.model_validate_json(res.content)

        if task_details.type == "normalizer":
            organization = task_details.p_item.data.raw_data.boefje_meta.organization
        else:
            organization = task_details.p_item.data.organization

        if organization != self.organization_code:
            raise TaskNotFoundError()

        return task_details

    def push_task(self, prioritized_item: PrioritizedItem) -> None:
        try:
            queue_name = f"{prioritized_item.data.type}-{self.organization_code}"
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

    def health(self) -> ServiceHealth:
        health_endpoint = self.session.get(f"{self._base_uri}/health")
        health_endpoint.raise_for_status()
        return ServiceHealth.model_validate_json(health_endpoint.content)

    def get_task_stats(self, task_type: str) -> Dict:
        try:
            res = self.session.get(f"{self._base_uri}/tasks/stats/{task_type}-{self.organization_code}")
            res.raise_for_status()
        except HTTPError:
            raise SchedulerError()
        task_stats = json.loads(res.content)
        return task_stats


def get_scheduler(organization_code: str) -> SchedulerClient:
    return SchedulerClient(settings.SCHEDULER_API, organization_code)
