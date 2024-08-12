from __future__ import annotations

import datetime
import json
import uuid
from enum import Enum
from functools import cached_property
from typing import Any

import httpx
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from httpx import ConnectError, HTTPError, HTTPStatusError, RequestError, codes
from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny, ValidationError

from rocky.health import ServiceHealth


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

    type: str = "normalizer"

    id: uuid.UUID | None = None
    normalizer: Normalizer
    raw_data: RawData


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    type: str = "boefje"

    id: uuid.UUID | None = None
    boefje: Boefje
    input_ooi: str | None = None
    organization: str


class ReportTask(BaseModel):
    type: str = "report"

    organization: str

    # TODO: add more fields


class TaskStatus(Enum):
    # Task has been created but not yet queued
    PENDING = "pending"

    # Task has been pushed onto queue and is ready to be picked up
    QUEUED = "queued"

    # Task has been picked up by a worker
    DISPATCHED = "dispatched"

    # Task has been picked up by a worker, and the worker indicates that it is
    # running.
    RUNNING = "running"

    # Task has been completed
    COMPLETED = "completed"

    # Task has failed
    FAILED = "failed"

    # Task has been cancelled
    CANCELLED = "cancelled"


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    scheduler_id: str
    schedule_id: str | None = None
    priority: int
    status: TaskStatus | None = TaskStatus.PENDING
    type: str | None = None
    hash: str | None = None
    data: SerializeAsAny[BoefjeTask | NormalizerTask]
    created_at: datetime.datetime | None = None
    modified_at: datetime.datetime | None = None


class ScheduleRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scheduler_id: str
    hash: str
    data: dict
    schedule: str
    deadline_at: datetime.datetime | None = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    hash: str
    data: dict
    enabled: bool
    schedule: str
    tasks: list[Task]
    deadline_at: datetime.datetime
    created_at: datetime.datetime
    modified_at: datetime.datetime


class PaginatedTasksResponse(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[Task]


class PaginatedSchedulesResponse(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[ScheduleResponse]


class LazyTaskList:
    HARD_LIMIT = 500

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
            limit = min(LazyTaskList.HARD_LIMIT, key.stop - offset or key.stop or LazyTaskList.HARD_LIMIT)

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
    message: str = _("The Scheduler has an unexpected error. Check the Scheduler logs for further details.")

    def __init__(self, *args: object, extra_message: str | None = None) -> None:
        super().__init__(*args)
        if extra_message is not None:
            self.message = extra_message + self.message

    def __str__(self):
        return str(self.message)


class SchedulerConnectError(SchedulerError):
    message = _("Could not connect to Scheduler. Service is possibly down.")


class SchedulerValidationError(SchedulerError):
    message = _("Your request could not be validated.")


class SchedulerTaskNotFound(SchedulerError):
    message = _("Task could not be found.")


class SchedulerTooManyRequestError(SchedulerError):
    message = _("Scheduler is receiving too many requests. Increase SCHEDULER_PQ_MAXSIZE or wait for task to finish.")


class SchedulerBadRequestError(SchedulerError):
    message = _("Bad request. Your request could not be interpreted by the Scheduler.")


class SchedulerConflictError(SchedulerError):
    message = _("The Scheduler has received a conflict. Your task is already in queue.")


class SchedulerHTTPError(SchedulerError):
    message = _("A HTTPError occurred. See Scheduler logs for more info.")


class SchedulerClient:
    def __init__(self, base_uri: str, organization_code: str):
        self._client = httpx.Client(base_url=base_uri)
        self.organization_code = organization_code

    # TODO: review the kwargs
    def list_schedules(self, **kwargs) -> PaginatedSchedulesResponse:
        try:
            kwargs = {k: v for k, v in kwargs.items() if v is not None}  # filter Nones from kwargs
            res = self._client.get("/schedules", params=kwargs)
            res.raise_for_status()
            return PaginatedSchedulesResponse.model_validate_json(res.content)
        except ValidationError:
            raise SchedulerValidationError(extra_message=_("Schedule list: "))
        except ConnectError:
            raise SchedulerConnectError(extra_message=_("Schedule list: "))

    def get_schedule_details(self, schedule_id: str) -> ScheduleResponse:
        try:
            res = self._client.get(f"/schedules/{schedule_id}")
            res.raise_for_status()
            return ScheduleResponse.model_validate_json(res.content)
        except ConnectError:
            raise SchedulerConnectError()

    def post_schedule(self, schedule: ScheduleRequest) -> ScheduleResponse:
        try:
            res = self._client.post(
                "/schedules",
                json=schedule.dict(exclude_none=True),
            )
            res.raise_for_status()
            return ScheduleResponse.model_validate_json(res.content)
        except ValidationError:
            raise SchedulerValidationError()
        except ConnectError:
            raise SchedulerConnectError()

    # TODO: arguments, a Schedule model, a dict?
    def patch_schedule(self, schedule_id: str, enabled: bool, schedule: str) -> None:
        # FIXME: this is just an example
        try:
            res = self._client.patch(
                f"/schedules/{schedule_id}",
                json={"enabled": enabled, "schedule": schedule},
            )
            res.raise_for_status()
        except ConnectError:
            raise SchedulerConnectError()

    def list_tasks(
        self,
        **kwargs,
    ) -> PaginatedTasksResponse:
        try:
            kwargs = {k: v for k, v in kwargs.items() if v is not None}  # filter Nones from kwargs
            res = self._client.get("/tasks", params=kwargs)
            return PaginatedTasksResponse.model_validate_json(res.content)
        except ValidationError:
            raise SchedulerValidationError(extra_message=_("Task list: "))
        except ConnectError:
            raise SchedulerConnectError(extra_message=_("Task list: "))

    def get_task_details(self, task_id: str) -> Task:
        try:
            res = self._client.get(f"/tasks/{task_id}")
            res.raise_for_status()
            task_details = Task.model_validate_json(res.content)

            if task_details.type == "normalizer":
                organization = task_details.data.raw_data.boefje_meta.organization
            else:
                organization = task_details.data.organization

            if organization != self.organization_code:
                raise SchedulerTaskNotFound()

            return task_details
        except ConnectError:
            raise SchedulerConnectError()

    def push_task(self, item: Task) -> None:
        try:
            queue_name = f"{item.data.type}-{self.organization_code}"
            res = self._client.post(
                f"/queues/{queue_name}/push",
                content=item.json(exclude_none=True),
                headers={"Content-Type": "application/json"},
            )
            res.raise_for_status()
        except HTTPStatusError as http_error:
            code = http_error.response.status_code
            if code == codes.TOO_MANY_REQUESTS:
                raise SchedulerTooManyRequestError()
            elif code == codes.BAD_REQUEST:
                raise SchedulerBadRequestError()
            elif code == codes.CONFLICT:
                raise SchedulerConflictError()
        except RequestError:
            raise SchedulerError()

    def health(self) -> ServiceHealth:
        try:
            health_endpoint = self._client.get("/health")
            health_endpoint.raise_for_status()
            return ServiceHealth.model_validate_json(health_endpoint.content)
        except HTTPError:
            raise SchedulerHTTPError()
        except ConnectError:
            raise SchedulerConnectError()

    def get_task_stats(self, task_type: str) -> dict:
        try:
            res = self._client.get(f"/tasks/stats/{task_type}-{self.organization_code}")
            res.raise_for_status()
        except ConnectError:
            raise SchedulerConnectError(extra_message=_("Task statistics: "))
        task_stats = json.loads(res.content)
        return task_stats


def scheduler_client(organization_code: str) -> SchedulerClient:
    return SchedulerClient(settings.SCHEDULER_API, organization_code)
