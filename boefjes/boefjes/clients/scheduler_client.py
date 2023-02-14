import logging
from typing import List, Optional, Union

import requests
import uuid

from enum import Enum
import datetime

from requests.adapters import HTTPAdapter, Retry

from boefjes.job_models import BoefjeMeta, NormalizerMeta
from pydantic import BaseModel, parse_obj_as


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
    hash: Optional[str]
    data: Union[BoefjeMeta, NormalizerMeta]


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


class SchedulerClientInterface:
    def get_queues(self) -> List[Queue]:
        raise NotImplementedError()

    def pop_item(self, queue: str) -> Optional[QueuePrioritizedItem]:
        raise NotImplementedError()

    def patch_task(self, task_id: str, status: TaskStatus) -> None:
        raise NotImplementedError()


class LogRetry(Retry):
    """Add a log when retrying a request"""

    def __init__(self, *args, skip_log=False, **kwargs):
        if not skip_log:
            logger.error("Failed to create desired call. Retrying...")

        super().__init__(*args, **kwargs)


class SchedulerAPIClient(SchedulerClientInterface):
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._session = requests.Session()

        max_retries = LogRetry(skip_log=True, total=6, backoff_factor=1)
        self._session.mount("https://", HTTPAdapter(max_retries=max_retries))
        self._session.mount("http://", HTTPAdapter(max_retries=max_retries))

    @staticmethod
    def _verify_response(response: requests.Response) -> None:
        response.raise_for_status()

    def get_queues(self) -> List[Queue]:
        response = self._session.get(f"{self.base_url}/queues")
        self._verify_response(response)

        return parse_obj_as(List[Queue], response.json())

    def pop_item(self, queue: str) -> Optional[QueuePrioritizedItem]:
        response = self._session.get(f"{self.base_url}/queues/{queue}/pop")
        self._verify_response(response)

        return parse_obj_as(Optional[QueuePrioritizedItem], response.json())

    def patch_task(self, task_id: str, status: TaskStatus) -> None:
        response = self._session.patch(f"{self.base_url}/tasks/{task_id}", json={"status": status.value})
        self._verify_response(response)

        logger.info(f"Set task status to {status} in the scheduler for task[{task_id}]")
