import tempfile
import time
from pathlib import Path
from typing import List, Union, Optional
from unittest import TestCase

from pydantic import parse_raw_as

from boefjes.app import SchedulerRuntimeManager
from boefjes.clients.scheduler_client import SchedulerClientInterface, Task, Queue
from boefjes.config import Settings
from boefjes.job_models import BoefjeMeta, NormalizerMeta
from boefjes.runtime import ItemHandler, StopWorking, RuntimeManager
from tests.stubs import get_dummy_data


class MockSchedulerClient(SchedulerClientInterface):
    def __init__(
        self, boefje_responses: List[bytes], normalizer_responses: List[bytes]
    ):
        self.boefje_responses = boefje_responses
        self.normalizer_responses = normalizer_responses

    def get_queues(self) -> List[Queue]:
        return parse_raw_as(List[Queue], self.boefje_responses.pop(0))

    def pop_task(self, queue: str) -> Optional[Task]:
        if RuntimeManager.Queue.BOEFJES.value in queue and self.boefje_responses:
            return parse_raw_as(Task, self.boefje_responses.pop(0))

        if (
            RuntimeManager.Queue.NORMALIZERS.value in queue
            and self.normalizer_responses
        ):
            return parse_raw_as(Task, self.normalizer_responses.pop(0))


class MockItemHandler(ItemHandler):
    def __init__(
        self,
        log_path: Path,
        sleep_time: float = 0.0,
        max_calls: int = 1,
        exception=StopWorking,
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
            f.write(item.json() + "\n")

        time.sleep(self.sleep_time)

    def get_all(self) -> List[Union[BoefjeMeta, NormalizerMeta]]:
        with open(self.log_path, "r") as f:
            f = [x for x in f]
            return [parse_raw_as(Union[BoefjeMeta, NormalizerMeta], x) for x in f]


class RuntimeTest(TestCase):
    def setUp(self) -> None:
        # This tests multiprocessing, so we use a file for interprocess communication
        self.tempdir = tempfile.TemporaryDirectory()

        self.item_handler = MockItemHandler(
            Path(self.tempdir.name) / "item_log", max_calls=2
        )
        queues_response = get_dummy_data("scheduler/queues_response.json")
        pop_response_boefje = get_dummy_data("scheduler/pop_response_boefje.json")
        pop_response_normalizer = get_dummy_data(
            "scheduler/pop_response_normalizer.json"
        )

        def client_factory():
            return MockSchedulerClient(
                3 * [queues_response, pop_response_boefje], [pop_response_normalizer]
            )

        self.runtime = SchedulerRuntimeManager(
            self.item_handler,
            client_factory,
            Settings(pool_size=1, poll_interval=0.01),
            "DEBUG",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_one_process(self) -> None:
        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(2, len(items))
        self.assertEqual("dns-records", items[0].boefje.id)
        self.assertEqual("dns-records", items[1].boefje.id)

    def test_two_processes(self) -> None:
        self.runtime.settings.pool_size = 2
        self.item_handler.sleep_time = 0.1

        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(4, len(items))

    def test_two_processes_exception(self) -> None:
        self.runtime.settings.pool_size = 2
        self.item_handler.max_calls = 0

        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        self.assertFalse(self.item_handler.log_path.exists())

    def test_two_processes_late_exception(self) -> None:
        self.runtime.settings.pool_size = 2
        self.item_handler.max_calls = 1

        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(2, len(items))

    def test_null(self) -> None:
        """This tests ensures we test the behaviour when the scheduler client returns None for the pop_task method"""
        self.item_handler.max_calls = 10
        self.runtime.run(RuntimeManager.Queue.BOEFJES)

        items = self.item_handler.get_all()
        self.assertEqual(3, len(items))

    def test_normalizer_queue(self) -> None:
        self.runtime.run(RuntimeManager.Queue.NORMALIZERS)

        items = self.item_handler.get_all()
        self.assertEqual(1, len(items))
        self.assertEqual("kat_dns_normalize", items[0].normalizer.id)
