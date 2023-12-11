import json
from multiprocessing import Manager
from pathlib import Path

import pytest

from boefjes.app import SchedulerWorkerManager
from boefjes.runtime_interfaces import WorkerManager
from tests.conftest import MockHandler, MockSchedulerClient
from tests.loading import get_dummy_data


def test_one_process(manager: SchedulerWorkerManager, item_handler: MockHandler) -> None:
    with pytest.raises(KeyboardInterrupt):
        manager.run(WorkerManager.Queue.BOEFJES)

    items = item_handler.get_all()
    assert len(items) == 2
    assert items[0].boefje.id == "dns-records"
    assert items[1].boefje.id == "dns-records"

    patched_tasks = manager.scheduler_client.get_all_patched_tasks()

    assert len(patched_tasks) == 3
    assert patched_tasks[0] == ("70da7d4f-f41f-4940-901b-d98a92e9014b", "completed")
    assert patched_tasks[1] == ("70da7d4f-f41f-4940-901b-d98a92e9014b", "completed")
    assert patched_tasks[2] == ("9071c9fd-2b9f-440f-a524-ef1ca4824fd4", "failed")


def test_two_processes(manager: SchedulerWorkerManager, item_handler: MockHandler) -> None:
    manager.settings.pool_size = 2
    manager.task_queue = Manager().Queue()

    with pytest.raises(KeyboardInterrupt):
        manager.run(WorkerManager.Queue.BOEFJES)

    items = item_handler.get_all()
    assert len(items) == 2

    patched_tasks = manager.scheduler_client.get_all_patched_tasks()
    assert len(patched_tasks) == 3
    assert patched_tasks.count(("70da7d4f-f41f-4940-901b-d98a92e9014b", "completed")) == 2
    assert patched_tasks.count(("9071c9fd-2b9f-440f-a524-ef1ca4824fd4", "failed")) == 1


def test_two_processes_exception(manager: SchedulerWorkerManager, item_handler: MockHandler, tmp_path) -> None:
    manager.scheduler_client = MockSchedulerClient(
        get_dummy_data("scheduler/queues_response.json"),
        [get_dummy_data("scheduler/should_crash.json")],
        [get_dummy_data("scheduler/pop_response_normalizer.json")],
        tmp_path / "patch_task_log",
    )

    manager.settings.pool_size = 2
    with pytest.raises(KeyboardInterrupt):
        manager.run(WorkerManager.Queue.BOEFJES)

    assert item_handler.queue.empty()
    assert manager.scheduler_client.log_path.exists()


def test_two_processes_handler_exception(manager: SchedulerWorkerManager, item_handler: MockHandler, tmp_path) -> None:
    manager.scheduler_client = MockSchedulerClient(
        get_dummy_data("scheduler/queues_response.json"),
        [get_dummy_data("scheduler/pop_response_boefje.json")] + 2 * [get_dummy_data("scheduler/should_crash.json")],
        [get_dummy_data("scheduler/pop_response_normalizer.json")],
        tmp_path / "patch_task_log",
    )

    manager.settings.pool_size = 2
    manager.task_queue = Manager().Queue()
    with pytest.raises(KeyboardInterrupt):
        manager.run(WorkerManager.Queue.BOEFJES)

    items = item_handler.get_all()
    assert len(items) == 1

    patched_tasks = manager.scheduler_client.get_all_patched_tasks()

    assert len(patched_tasks) == 3
    # Handler starts raising an Exception from the second call onward,
    # so we have 2 completed tasks and 4 failed tasks.
    assert patched_tasks.count(("70da7d4f-f41f-4940-901b-d98a92e9014b", "completed")) == 1
    assert patched_tasks.count(("9071c9fd-2b9f-440f-a524-ef1ca4824fd4", "failed")) == 2


def test_two_processes_cleanup_unfinished_tasks(
    manager: SchedulerWorkerManager, item_handler: MockHandler, tmp_path
) -> None:
    """
    Push 3 slow tasks to 2 workers,
    then crash (from popping from an empty queue),
    then clean up task on queue and the tasks being handled
    """

    manager.scheduler_client = MockSchedulerClient(
        get_dummy_data("scheduler/queues_response.json"),
        3 * [get_dummy_data("scheduler/pop_response_boefje.json")],
        [],
        tmp_path / "patch_task_log",
    )
    manager.settings.pool_size = 2
    manager.task_queue = Manager().Queue()

    item_handler.sleep_time = 200

    with pytest.raises(KeyboardInterrupt):
        manager.run(WorkerManager.Queue.BOEFJES)

    items = item_handler.get_all()
    assert len(items) == 0

    patched_tasks = manager.scheduler_client.get_all_patched_tasks()
    assert len(patched_tasks) == 1

    # Task was running but main process crashed intentionally and cleaned it up
    assert patched_tasks.count(("70da7d4f-f41f-4940-901b-d98a92e9014b", "failed")) == 1

    # Tasks (one with the same id) was still unhandled the queue and pushed back to the scheduler by the main process
    assert manager.scheduler_client._pushed_items["70da7d4f-f41f-4940-901b-d98a92e9014b"][0] == "boefje"
    assert json.loads(
        manager.scheduler_client._pushed_items["70da7d4f-f41f-4940-901b-d98a92e9014b"][1].json()
    ) == json.loads(get_dummy_data("scheduler/pop_response_boefje.json"))


def test_normalizer_queue(manager: SchedulerWorkerManager, item_handler: MockHandler) -> None:
    with pytest.raises(KeyboardInterrupt):
        manager.run(WorkerManager.Queue.NORMALIZERS)

    items = item_handler.get_all()
    assert len(items) == 1
    assert items[0].normalizer.id == "kat_dns_normalize"


def test_null(manager: SchedulerWorkerManager, tmp_path: Path, item_handler: MockHandler):
    manager.scheduler_client = MockSchedulerClient(
        get_dummy_data("scheduler/queues_response.json"),
        3 * [get_dummy_data("scheduler/pop_response_boefje.json")],
        [get_dummy_data("scheduler/pop_response_normalizer.json")],
        tmp_path / "patch_task_log",
        iterations_to_wait_for_exception=2,
    )

    with pytest.raises(KeyboardInterrupt):
        manager.run(WorkerManager.Queue.BOEFJES)

    items = item_handler.get_all()
    patched_tasks = manager.scheduler_client.get_all_patched_tasks()

    assert len(items) == 3
    assert len(patched_tasks) == 3
    assert patched_tasks[0] == ("70da7d4f-f41f-4940-901b-d98a92e9014b", "completed")
    assert patched_tasks[2] == ("70da7d4f-f41f-4940-901b-d98a92e9014b", "completed")
