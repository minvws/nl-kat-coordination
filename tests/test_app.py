import tempfile
import time
from pathlib import Path
from typing import List, Union, Optional
from unittest import TestCase

from pydantic import parse_raw_as

from boefjes.app import SchedulerRuntimeManager
from boefjes.clients.scheduler_client import SchedulerClientInterface, QueuePrioritizedItem, Queue, TaskStatus
from boefjes.config import Settings
from boefjes.job_models import BoefjeMeta, NormalizerMeta
from boefjes.runtime_interfaces import Handler, RuntimeManager
from tests.stubs import get_dummy_data


class MockSchedulerClient(SchedulerClientInterface):
    def __init__(self, boefje_responses: List[bytes], normalizer_responses: List[bytes], log_path: Path):
        self.boefje_responses = boefje_responses
        self.normalizer_responses = normalizer_responses
        self.log_path = log_path

    def get_queues(self) -> List[Queue]:
        return parse_raw_as(List[Queue], self.boefje_responses.pop(0))

    def pop_item(self, queue: str) -> Optional[QueuePrioritizedItem]:
        if RuntimeManager.Queue.BOEFJES.value in queue and self.boefje_responses:
            return parse_raw_as(QueuePrioritizedItem, self.boefje_responses.pop(0))

        if RuntimeManager.Queue.NORMALIZERS.value in queue and self.normalizer_responses:
            return parse_raw_as(QueuePrioritizedItem, self.normalizer_responses.pop(0))

    def patch_task(self, task_id: str, status: TaskStatus) -> None:
        with open(self.log_path, "a") as f:
            f.write(f"{task_id},{status.value}\n")

    def get_all_patched_tasks(self) -> List[List[str]]:
        with open(self.log_path, "r") as f:
            return [x.strip().split(",") for x in f]


class MockHandler(Handler):
    def __init__(
        self,
        log_path: Path,
        sleep_time: float = 0.0,
        max_calls: int = 2,
        exception=Exception,
    ):
        self.log_path = log_path
        self.sleep_time = sleep_time
        self.max_calls = max_calls
        self.calls = 0
        self.exception = exception

    def handle(self, item: Union[BoefjeMeta, NormalizerMeta]):
        if self.calls >= self.max_calls:
            raise self.exception()

        self.calls += 1

        with open(self.log_path, "a") as f:
            f.write(f"{item.json()}\n")

        time.sleep(self.sleep_time)

    def get_all(self) -> List[Union[BoefjeMeta, NormalizerMeta]]:
        with open(self.log_path, "r") as f:
            f = [x for x in f]
            return [parse_raw_as(Union[BoefjeMeta, NormalizerMeta], x) for x in f]


class AppTest(TestCase):
    def setUp(self) -> None:
        # This tests multiprocessing, so we use a file for mocking interprocess communication
        self.tempdir = tempfile.TemporaryDirectory()

        self.item_handler = MockHandler(Path(self.tempdir.name) / "item_log")
        queues_response = get_dummy_data("scheduler/queues_response.json")
        pop_response_boefje = get_dummy_data("scheduler/pop_response_boefje.json")
        pop_response_normalizer = get_dummy_data("scheduler/pop_response_normalizer.json")

        self.scheduler_client = MockSchedulerClient(
            3 * [queues_response, pop_response_boefje],
            [pop_response_normalizer],
            Path(self.tempdir.name) / "patch_task_log",
        )

        def client_factory():
            return self.scheduler_client

        self.runtime = SchedulerRuntimeManager(
            self.item_handler, client_factory, Settings(pool_size=1, poll_interval=0.01), "DEBUG"
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_one_process(self) -> None:
        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(2, len(items))
        self.assertEqual("dns-records", items[0].boefje.id)
        self.assertEqual("dns-records", items[1].boefje.id)

        patched_tasks = self.scheduler_client.get_all_patched_tasks()
        self.assertEqual(3, len(patched_tasks))
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[0])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[1])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "failed"], patched_tasks[2])

    def test_two_processes(self) -> None:
        self.runtime.settings.pool_size = 2
        self.item_handler.sleep_time = 0.1

        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(4, len(items))

        patched_tasks = self.scheduler_client.get_all_patched_tasks()
        self.assertEqual(6, len(patched_tasks))
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[0])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[3])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "failed"], patched_tasks[4])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "failed"], patched_tasks[5])

    def test_two_processes_exception(self) -> None:
        self.runtime.settings.pool_size = 2
        self.item_handler.max_calls = 0

        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        self.assertFalse(self.item_handler.log_path.exists())
        self.assertTrue(self.scheduler_client.log_path.exists())

    def test_two_processes_late_exception(self) -> None:
        self.runtime.settings.pool_size = 2
        self.item_handler.max_calls = 1

        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(2, len(items))

        patched_tasks = self.scheduler_client.get_all_patched_tasks()
        self.assertEqual(6, len(patched_tasks))
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[0])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[1])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "failed"], patched_tasks[2])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "failed"], patched_tasks[3])

    def test_two_processes_handler_exception(self) -> None:
        self.runtime.settings.pool_size = 2
        self.item_handler.max_calls = 1

        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(2, len(items))

        patched_tasks = self.scheduler_client.get_all_patched_tasks()
        self.assertEqual(6, len(patched_tasks))
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[0])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[1])
        self.assertEqual(
            ["70da7d4f-f41f-4940-901b-d98a92e9014b", "failed"], patched_tasks[2]
        )  # Handler starts raising an Exception from the second call onward
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "failed"], patched_tasks[3])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "failed"], patched_tasks[4])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "failed"], patched_tasks[5])

    def test_null(self) -> None:
        """This tests ensures we test the behaviour when the scheduler client returns None for the pop_task method"""
        self.item_handler.max_calls = 10
        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(3, len(items))

        patched_tasks = self.scheduler_client.get_all_patched_tasks()
        self.assertEqual(3, len(patched_tasks))
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[0])
        self.assertEqual(["70da7d4f-f41f-4940-901b-d98a92e9014b", "completed"], patched_tasks[2])

    def test_normalizer_queue(self) -> None:
        self.runtime.run(RuntimeManager.Queue.NORMALIZERS)

        items = self.item_handler.get_all()
        self.assertEqual(1, len(items))
        self.assertEqual("kat_dns_normalize", items[0].normalizer.id)
