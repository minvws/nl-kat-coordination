import multiprocessing
import time
from datetime import datetime, timezone
from multiprocessing import Manager
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import parse_raw_as

from boefjes.app import SchedulerWorkerManager
from boefjes.clients.scheduler_client import Queue, QueuePrioritizedItem, SchedulerClientInterface, Task, TaskStatus
from boefjes.config import Settings
from boefjes.job_models import BoefjeMeta, NormalizerMeta
from boefjes.runtime_interfaces import Handler, WorkerManager
from tests.stubs import get_dummy_data


class MockSchedulerClient(SchedulerClientInterface):
    def __init__(
        self,
        queue_response: bytes,
        boefje_responses: List[bytes],
        normalizer_responses: List[bytes],
        log_path: Path,
        raise_on_empty_queue: Exception = KeyboardInterrupt,
        iterations_to_wait_for_exception: int = 0,
        sleep_time: int = 0.1,
    ):
        self.queue_response = queue_response
        self.boefje_responses = boefje_responses
        self.normalizer_responses = normalizer_responses
        self.log_path = log_path
        self.raise_on_empty_queue = raise_on_empty_queue
        self.iterations_to_wait_for_exception = iterations_to_wait_for_exception
        self.sleep_time = sleep_time

        self._iterations = 0
        self._tasks: Dict[str, Task] = multiprocessing.Manager().dict()
        self._popped_items: Dict[str, QueuePrioritizedItem] = multiprocessing.Manager().dict()
        self._pushed_items: Dict[str, Tuple[str, QueuePrioritizedItem]] = multiprocessing.Manager().dict()

    def get_queues(self) -> List[Queue]:
        time.sleep(self.sleep_time)
        return parse_raw_as(List[Queue], self.queue_response)

    def pop_item(self, queue: str) -> Optional[QueuePrioritizedItem]:
        time.sleep(self.sleep_time)

        try:
            if WorkerManager.Queue.BOEFJES.value in queue:
                p_item = parse_raw_as(QueuePrioritizedItem, self.boefje_responses.pop(0))
                self._popped_items[str(p_item.id)] = p_item
                self._tasks[str(p_item.id)] = self._task_from_id(p_item.id)
                return p_item

            if WorkerManager.Queue.NORMALIZERS.value in queue:
                p_item = parse_raw_as(QueuePrioritizedItem, self.normalizer_responses.pop(0))
                self._popped_items[str(p_item.id)] = p_item
                return p_item
        except IndexError:
            raise self.raise_on_empty_queue

    def patch_task(self, task_id: UUID, status: TaskStatus) -> None:
        with self.log_path.open("a") as f:
            f.write(f"{task_id},{status.value}\n")

        task = self._task_from_id(task_id) if task_id not in self._tasks else self._tasks[str(task_id)]
        task.status = status
        self._tasks[str(task_id)] = task

    def get_all_patched_tasks(self) -> List[Tuple[str, ...]]:
        with self.log_path.open() as f:
            return [tuple(x.strip().split(",")) for x in f]

    def get_task(self, task_id: UUID) -> Task:
        return self._task_from_id(task_id) if task_id not in self._tasks else self._tasks[str(task_id)]

    def _task_from_id(self, task_id: UUID):
        return Task(
            id=task_id,
            scheduler_id="test",
            type="test",
            p_item=self._popped_items[str(task_id)],
            status=TaskStatus.DISPATCHED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

    def push_item(self, queue_id: str, p_item: QueuePrioritizedItem) -> None:
        self._pushed_items[str(p_item.id)] = (queue_id, p_item)


class MockHandler(Handler):
    def __init__(self, exception=Exception):
        self.sleep_time = 0
        self.queue = Manager().Queue()
        self.exception = exception

    def handle(self, item: Union[BoefjeMeta, NormalizerMeta]):
        if str(item.id) == "9071c9fd-2b9f-440f-a524-ef1ca4824fd4":
            raise self.exception()

        time.sleep(self.sleep_time)
        self.queue.put(item)

    def get_all(self) -> List[Union[BoefjeMeta, NormalizerMeta]]:
        return [self.queue.get() for _ in range(self.queue.qsize())]


@pytest.fixture
def item_handler(tmp_path: Path):
    return MockHandler()


@pytest.fixture
def manager(item_handler: MockHandler, tmp_path: Path) -> SchedulerWorkerManager:
    scheduler_client = MockSchedulerClient(
        get_dummy_data("scheduler/queues_response.json"),
        2 * [get_dummy_data("scheduler/pop_response_boefje.json")] + [get_dummy_data("scheduler/should_crash.json")],
        [get_dummy_data("scheduler/pop_response_normalizer.json")],
        tmp_path / "patch_task_log",
    )

    return SchedulerWorkerManager(item_handler, scheduler_client, Settings(pool_size=1, poll_interval=0.01), "DEBUG")


@pytest.fixture
def api(tmp_path):
    from boefjes.api import app

    return TestClient(app)
