import tempfile
import time
from pathlib import Path
from typing import List, Optional, Union
from unittest import TestCase

import pytest
from pydantic import parse_raw_as

from boefjes.app import SchedulerWorkerManager
from boefjes.clients.scheduler_client import Queue, QueuePrioritizedItem, SchedulerClientInterface, TaskStatus
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


class MockHandler(Handler):
    def __init__(self, log_path: Path, sleep_time: float = 0.0, exception=Exception):
        self.log_path = log_path
        self.sleep_time = sleep_time
        self.exception = exception

    def handle(self, item: Union[BoefjeMeta, NormalizerMeta]):
        if item.id == "9071c9fd-2b9f-440f-a524-ef1ca4824fd4":
            raise self.exception()

        with self.log_path.open("a") as f:
            f.write(f"{item.json()}\n")

        time.sleep(self.sleep_time)

    def get_all(self) -> List[Union[BoefjeMeta, NormalizerMeta]]:
        with self.log_path.open() as f:
            f = [x for x in f]
            return [parse_raw_as(Union[BoefjeMeta, NormalizerMeta], x) for x in f]


class AppTest(TestCase):
    def setUp(self) -> None:
        # This tests multiprocessing, so we use a file for mocking interprocess communication
        self.tempdir = tempfile.TemporaryDirectory()

        self.item_handler = MockHandler(Path(self.tempdir.name) / "item_log")
        queues_response = get_dummy_data("scheduler/queues_response.json")
        pop_response_boefje = get_dummy_data("scheduler/pop_response_boefje.json")
        pop_response_boefje_should_crash = get_dummy_data("scheduler/pop_response_boefje_should_crash.json")
        pop_response_normalizer = get_dummy_data("scheduler/pop_response_normalizer.json")

        self.scheduler_client = MockSchedulerClient(
            queues_response,
            [pop_response_boefje, pop_response_boefje, pop_response_boefje_should_crash],
            [pop_response_normalizer],
            Path(self.tempdir.name) / "patch_task_log",
        )

        def client_factory():
            return self.scheduler_client

        self.runtime = SchedulerWorkerManager(
            self.item_handler, client_factory, Settings(pool_size=1, poll_interval=0.01), "DEBUG"
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_one_process(self) -> None:
        with pytest.raises(KeyboardInterrupt):
            self.runtime.run(WorkerManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(2, len(items))
        self.assertEqual("dns-records", items[0].boefje.id)
        self.assertEqual("dns-records", items[1].boefje.id)

        patched_tasks = self.scheduler_client.get_all_patched_tasks()
        self.assertEqual(3, len(patched_tasks))
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[0])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[1])
        self.assertEqual(["9071c9fd-2b9f-440f-a524-ef1ca4824fd4", "failed"], patched_tasks[2])

    def test_two_processes(self) -> None:
        self.runtime.settings.pool_size = 2
        with pytest.raises(KeyboardInterrupt):
            self.runtime.run(WorkerManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(2, len(items))

        patched_tasks = self.scheduler_client.get_all_patched_tasks()
        self.assertEqual(3, len(patched_tasks))
        self.assertEqual(patched_tasks.count(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"]), 2)
        self.assertEqual(patched_tasks.count(["9071c9fd-2b9f-440f-a524-ef1ca4824fd4", "failed"]), 1)

    def test_two_processes_exception(self) -> None:
        self.scheduler_client.boefje_responses = [get_dummy_data("scheduler/pop_response_boefje_should_crash.json")]
        self.runtime.settings.pool_size = 2
        with pytest.raises(KeyboardInterrupt):
            self.runtime.run(WorkerManager.Queue.BOEFJES)

        self.assertFalse(self.item_handler.log_path.exists())
        self.assertTrue(self.scheduler_client.log_path.exists())

    def test_two_processes_handler_exception(self) -> None:
        self.scheduler_client.boefje_responses[1:] = [
            get_dummy_data("scheduler/pop_response_boefje_should_crash.json"),
            get_dummy_data("scheduler/pop_response_boefje_should_crash.json"),
        ]
        self.runtime.settings.pool_size = 2
        with pytest.raises(KeyboardInterrupt):
            self.runtime.run(WorkerManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(1, len(items))

        patched_tasks = self.scheduler_client.get_all_patched_tasks()
        self.assertEqual(3, len(patched_tasks))
        # Handler starts raising an Exception from the second call onward,
        # so we have 2 completed tasks and 4 failed tasks.
        self.assertEqual(patched_tasks.count(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"]), 1)
        self.assertEqual(patched_tasks.count(["9071c9fd-2b9f-440f-a524-ef1ca4824fd4", "failed"]), 2)

    def test_null(self) -> None:
        """This tests ensures we test the behaviour when the scheduler client returns None for the pop_task method"""
        self.scheduler_client.boefje_responses[-1] = get_dummy_data("scheduler/pop_response_boefje.json")
        self.scheduler_client.iterations_to_wait_for_exception = 2

        with pytest.raises(KeyboardInterrupt):
            self.runtime.run(WorkerManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(3, len(items))

        patched_tasks = self.scheduler_client.get_all_patched_tasks()
        self.assertEqual(3, len(patched_tasks))
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[0])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[2])

    def test_normalizer_queue(self) -> None:
        with pytest.raises(KeyboardInterrupt):
            self.runtime.run(WorkerManager.Queue.NORMALIZERS)

        items = self.item_handler.get_all()
        self.assertEqual(1, len(items))
        self.assertEqual("kat_dns_normalize", items[0].normalizer.id)
