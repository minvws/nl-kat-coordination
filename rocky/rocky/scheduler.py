from __future__ import annotations

import datetime
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

import requests
from django.conf import settings
from pydantic import BaseModel, Field

from rocky.health import ServiceHealth


class Boefje(BaseModel):
    """Boefje representation."""

    id: str
    name: Optional[str]
    description: Optional[str]
    repository_id: Optional[str]
    version: Optional[str] = Field(default=None)
    scan_level: Optional[int] = Field(default=None)
    consumes: Optional[Union[str, Set[str]]]
    produces: Optional[Set[str]]


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: str
    boefje: Boefje
    input_ooi: Optional[str]
    arguments: Dict[str, Any]
    organization: str
    started_at: Optional[datetime.datetime]
    ended_at: Optional[datetime.datetime]


class RawData(BaseModel):
    id: Optional[str]
    boefje_meta: BoefjeMeta
    mime_types: List[Dict[str, str]]
    secure_hash: Optional[str]
    hash_retrieval_link: Optional[str]


class Normalizer(BaseModel):
    """Normalizer representation."""

    id: Optional[str]
    name: Optional[str]
    version: Optional[str] = Field(default=None)


class NormalizerMeta(BaseModel):
    id: str
    raw_file_id: str
    normalizer: Normalizer
    started_at: datetime.datetime
    ended_at: datetime.datetime


class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    id: Optional[str]
    normalizer: Normalizer
    raw_data: RawData


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    id: Optional[str]
    boefje: Boefje
    input_ooi: Optional[str]
    organization: str


class QueuePrioritizedItem(BaseModel):
    """Representation of a queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue prioritized items to a JSON
    representation.
    """

    id: uuid.UUID
    priority: int
    hash: Optional[str]
    data: Union[BoefjeTask, NormalizerTask]


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str
    scheduler_id: str
    type: str
    p_item: QueuePrioritizedItem
    status: TaskStatus
    created_at: datetime.datetime
    modified_at: datetime.datetime

    class Config:
        orm_mode = True


class PaginatedTasksResponse(BaseModel):
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[Task]


class LazyTaskList:
    def __init__(
        self,
        scheduler_client: SchedulerClient,
        scheduler_id: str,
        object_type: Optional[str] = None,
        status: Optional[str] = None,
        min_created_at: Optional[datetime.datetime] = None,
        max_created_at: Optional[datetime.datetime] = None,
        filters: Optional[List[Dict]] = None,
    ):
        self.scheduler_client = scheduler_client

        self.scheduler_id = scheduler_id
        self.object_type = object_type
        self.status = status
        self.min_created_at = min_created_at
        self.max_created_at = max_created_at
        self.filters = filters

        self._count = None

    @property
    def count(self) -> int:
        if self._count is None:
            self._count = self.scheduler_client.list_tasks(
                self.scheduler_id,
                type=self.object_type,
                limit=0,
                status=self.status,
                min_created_at=self.min_created_at,
                max_created_at=self.max_created_at,
                filters=self.filters,
            ).count
        return self._count

    def __len__(self):
        return self.count

    def __getitem__(self, key) -> List[Task]:
        if isinstance(key, slice):
            offset = key.start or 0
            limit = key.stop - offset
        elif isinstance(key, int):
            offset = key
            limit = 1
        else:
            raise TypeError("Invalid slice argument type.")

        res = self.scheduler_client.list_tasks(
            self.scheduler_id,
            type=self.object_type,
            limit=limit,
            offset=offset,
            status=self.status,
            min_created_at=self.min_created_at,
            max_created_at=self.max_created_at,
            filters=self.filters,
        )

        self._count = res.count
        return res.results


class SchedulerClient:
    def __init__(self, base_uri: str):
        self.session = requests.Session()
        self._base_uri = base_uri

    def list_tasks(
        self,
        scheduler_id: str,
        type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        min_created_at: Optional[datetime.datetime] = None,
        max_created_at: Optional[datetime.datetime] = None,
        filters: Optional[List[Dict]] = None,
    ) -> PaginatedTasksResponse:
        params = {
            "scheduler_id": scheduler_id,
            "type": type,
            "limit": limit,
            "offset": offset,
            "status": status,
            "min_created_at": min_created_at,
            "max_created_at": max_created_at,
        }

        res = self.session.get(f"{self._base_uri}/tasks", params=params, json=filters)
        return PaginatedTasksResponse.parse_raw(res.text)

    def get_lazy_task_list(
        self,
        scheduler_id: str,
        object_type: Optional[str] = None,
        status: Optional[str] = None,
        min_created_at: Optional[datetime.datetime] = None,
        max_created_at: Optional[datetime.datetime] = None,
        filters: Optional[List[Dict]] = None,
    ) -> LazyTaskList:
        return LazyTaskList(self, scheduler_id, object_type, status, min_created_at, max_created_at, filters)

    def get_task_details(self, task_id):
        res = self.session.get(f"{self._base_uri}/tasks/{task_id}")
        return res.json()

    def push_task(self, queue_name: str, prioritized_item: QueuePrioritizedItem) -> None:
        res = self.session.post(f"{self._base_uri}/queues/{queue_name}/push", data=prioritized_item.json())
        res.raise_for_status()

    def health(self) -> ServiceHealth:
        health_endpoint = self.session.get(f"{self._base_uri}/health")
        health_endpoint.raise_for_status()
        return ServiceHealth.parse_raw(health_endpoint.content)


client = SchedulerClient(settings.SCHEDULER_API)
