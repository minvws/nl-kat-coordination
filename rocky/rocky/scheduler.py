from __future__ import annotations

import collections
import datetime
import uuid
from enum import Enum
from logging import getLogger
from typing import Any

import httpx
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from httpx import HTTPError, HTTPStatusError, RequestError, codes
from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

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
    def __init__(
        self,
        scheduler_client: SchedulerClient,
        **kwargs,
    ):
        self.scheduler_client = scheduler_client
        self.kwargs = kwargs
        self._count: int | None = None

    @property
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
            limit = key.stop - offset
        elif isinstance(key, int):
            offset = key
            limit = 1
        else:
            raise TypeError("Invalid slice argument type.")

        logger.info("Getting max %s lazy items at offset %s with filter %s", limit, offset, self.kwargs)
        res = self.scheduler_client.list_tasks(
            limit=limit,
            offset=offset,
            **self.kwargs,
        )

        self._count = res.count
        return res.results


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
        self._client = httpx.Client(base_url=base_uri)

    def list_tasks(
        self,
        **kwargs,
    ) -> PaginatedTasksResponse:
        filter_key = "filters"
        params = {k: v for k, v in kwargs.items() if v is not None if k != filter_key}  # filter Nones from kwargs
        endpoint = "/tasks"
        res = self._client.post(endpoint, params=params, json=kwargs.get(filter_key, None))
        try:
            res.raise_for_status()
        except HTTPStatusError as exc:
            logger.warning(
                "Unexpected response %s from endpoint %s with args %s which returns code %s. Exception: %s",
                res.content,
                endpoint,
                kwargs,
                res.status_code,
                exc,
            )
        return PaginatedTasksResponse.model_validate_json(res.content)

    def get_lazy_task_list(
        self,
        scheduler_id: str | None,
        task_type: str | None = None,
        status: str | None = None,
        min_created_at: datetime.datetime | None = None,
        max_created_at: datetime.datetime | None = None,
        input_ooi: str | None = None,
        plugin_id: str | None = None,
        boefje_name: str | None = None,
        filters: dict | None = None,
    ) -> LazyTaskList:
        return LazyTaskList(
            self,
            scheduler_id=scheduler_id,
            task_type=task_type,
            status=status,
            min_created_at=min_created_at,
            max_created_at=max_created_at,
            input_ooi=input_ooi,
            plugin_id=plugin_id,
            boefje_name=boefje_name,
            filters=filters,
        )

    def get_task_details(self, organization_code: str, task_id: str) -> Task:
        res = self._client.get(f"/tasks/{task_id}")
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
            res = self._client.post(
                f"/queues/{queue_name}/push",
                content=prioritized_item.json(),
                headers={"Content-Type": "application/json"},
            )
            res.raise_for_status()
        except HTTPStatusError as http_error:
            code = http_error.response.status_code
            if code == codes.TOO_MANY_REQUESTS:
                raise TooManyRequestsError()
            elif code == codes.BAD_REQUEST:
                raise BadRequestError()
            elif code == codes.CONFLICT:
                raise ConflictError()
            else:
                raise SchedulerError()
        except RequestError:
            raise SchedulerError()

    def health(self) -> ServiceHealth:
        health_endpoint = self._client.get("/health")
        health_endpoint.raise_for_status()
        return ServiceHealth.model_validate_json(health_endpoint.content)

    def _get(self, path: str) -> dict:
        """Helper to do a get request."""
        try:
            res = self._client.get(path)
            res.raise_for_status()
        except HTTPError:
            raise SchedulerError(path)
        return res.json()

    def _get_task_stats(self, scheduler_id: str) -> dict:
        """Return task stats for specific scheduler."""
        return self._get(f"/tasks/stats/{scheduler_id}")

    def get_task_stats(self, organization_code: str, task_type: str) -> dict:
        """Return task stats for specific organization and task combination."""
        return self._get_task_stats(scheduler_id=f"{task_type}-{organization_code}")

    @staticmethod
    def _merge_stat_dicts(dicts: list[dict]) -> dict:
        """Merge multiple stats dicts."""
        stat_sum: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        for dct in dicts:
            for timeslot, counts in dct.items():
                stat_sum[timeslot].update(counts)
        return dict(stat_sum)

    def get_combined_schedulers_stats(self, scheduler_ids: list) -> dict:
        """Return merged stats for a set of scheduler ids."""
        return SchedulerClient._merge_stat_dicts(
            dicts=[self._get_task_stats(scheduler_id=scheduler_id) for scheduler_id in scheduler_ids]
        )


client = SchedulerClient(settings.SCHEDULER_API)
