import boefjes.api
from boefjes.clients.scheduler_client import TaskStatus


def test_healthz(api):
    response = api.get("/healthz")
    assert response.status_code == 200
    assert response.text == '"OK"'


def test_boefje_input_running(api):
    scheduler_client = boefjes.api.scheduler_client
    task = scheduler_client.pop_item("boefje")
    scheduler_client.patch_task(task.id, TaskStatus.RUNNING)

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


def test_boefje_input_not_running(api):
    scheduler_client = boefjes.api.scheduler_client
    scheduler_client.pop_item("boefje")

    response = api.get("/api/v0/tasks/70da7d4f-f41f-4940-901b-d98a92e9014b")
    assert response.status_code == 403
