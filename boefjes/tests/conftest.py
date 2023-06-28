from multiprocessing import Queue as MultiprocessingQueue
from pathlib import Path
from typing import List, Optional, Union

import pytest
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
    ):
        self.queue_response = queue_response
        self.boefje_responses = boefje_responses
        self.normalizer_responses = normalizer_responses
        self.log_path = log_path
        self.raise_on_empty_queue = raise_on_empty_queue
        self.iterations_to_wait_for_exception = iterations_to_wait_for_exception
        self.iterations = 0

    def get_queues(self) -> List[Queue]:
        return parse_raw_as(List[Queue], self.queue_response)

    def pop_item(self, queue: str) -> Optional[QueuePrioritizedItem]:
        try:
            if WorkerManager.Queue.BOEFJES.value in queue:
                return parse_raw_as(QueuePrioritizedItem, self.boefje_responses.pop(0))

            if WorkerManager.Queue.NORMALIZERS.value in queue:
                return parse_raw_as(QueuePrioritizedItem, self.normalizer_responses.pop(0))
        except IndexError:
            raise self.raise_on_empty_queue

    def patch_task(self, task_id: str, status: TaskStatus) -> None:
        with self.log_path.open("a") as f:
            f.write(f"{task_id},{status.value}\n")

    def get_all_patched_tasks(self) -> List[List[str]]:
        with self.log_path.open() as f:
            return [x.strip().split(",") for x in f]

    def get_task(self, task_id: str) -> Task:
        pass


class MockHandler(Handler):
    def __init__(self, exception=Exception):
        self.queue = MultiprocessingQueue()
        self.exception = exception

    def handle(self, item: Union[BoefjeMeta, NormalizerMeta]):
        if item.id == "9071c9fd-2b9f-440f-a524-ef1ca4824fd4":
            raise self.exception()

        self.queue.put(item)

    def get_all(self) -> List[Union[BoefjeMeta, NormalizerMeta]]:
        return [self.queue.get() for _ in range(self.queue.qsize())]


@pytest.fixture
def item_handler(tmp_path: Path):
    return MockHandler()


@pytest.fixture
def manager(item_handler: MockHandler, tmp_path: Path) -> SchedulerWorkerManager:
    def client_factory():
        return MockSchedulerClient(
            get_dummy_data("scheduler/queues_response.json"),
            2 * [get_dummy_data("scheduler/pop_response_boefje.json")]
            + [get_dummy_data("scheduler/should_crash.json")],
            [get_dummy_data("scheduler/pop_response_normalizer.json")],
            tmp_path / "patch_task_log",
        )

    return SchedulerWorkerManager(item_handler, client_factory, Settings(pool_size=1, poll_interval=0.01), "DEBUG")
