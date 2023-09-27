from pathlib import Path

import boefjes.api
from boefjes.clients.scheduler_client import TaskStatus
from tests.conftest import MockSchedulerClient
from tests.stubs import get_dummy_data


def _mocked_scheduler_client(tmp_path: Path):
    return MockSchedulerClient(
        get_dummy_data("scheduler/queues_response.json"),
        [get_dummy_data("scheduler/pop_response_boefje_no_ooi.json")],
        [],
        tmp_path / "patch_task_log",
    )


def test_healthz(api):
    response = api.get("/healthz")
    assert response.status_code == 200
    assert response.text == '"OK"'


def test_boefje_input_running(api, tmp_path):
    scheduler_client = _mocked_scheduler_client(tmp_path)
    task = scheduler_client.pop_item("boefje")
    scheduler_client.patch_task(task.id, TaskStatus.RUNNING)
    api.app.dependency_overrides[boefjes.api.get_scheduler_client] = lambda: scheduler_client

    response = api.get("/api/v0/tasks/70da7d4f-f41f-4940-901b-d98a92e9014b")
    assert response.status_code == 200
    assert response.json() == {
        "task_id": "70da7d4f-f41f-4940-901b-d98a92e9014b",
        "output_url": "http://placeholder:8006/api/v0/tasks/70da7d4f-f41f-4940-901b-d98a92e9014b",
        "boefje_meta": {
            "arguments": {},
            "boefje": {"id": "dns-records", "version": None},
            "ended_at": None,
            "environment": {},
            "id": "70da7d4f-f41f-4940-901b-d98a92e9014b",
            "input_ooi": "",
            "organization": "_dev",
            "runnable_hash": None,
            "started_at": None,
        },
    }


def test_boefje_input_not_running(api, tmp_path):
    scheduler_client = _mocked_scheduler_client(tmp_path)
    scheduler_client.pop_item("boefje")
    api.app.dependency_overrides[boefjes.api.get_scheduler_client] = lambda: scheduler_client

    response = api.get("/api/v0/tasks/70da7d4f-f41f-4940-901b-d98a92e9014b")
    assert response.status_code == 403
