import uuid
from typing import Any

from httpx import Client, HTTPTransport, Response
from pydantic import TypeAdapter

# A deliberate relative import to make this module self-contained
from .interfaces import BoefjeOutput, BoefjeStorageInterface, Queue, SchedulerClientInterface, Task, TaskStatus, \
    PaginatedTasksResponse


class BoefjeAPIClient(SchedulerClientInterface, BoefjeStorageInterface):
    def __init__(self, base_url: str, outgoing_request_timeout: int, oci_image: str | None):
        self._session = Client(base_url=base_url, transport=HTTPTransport(retries=6), timeout=outgoing_request_timeout)
        self.oci_image = oci_image

    @staticmethod
    def _verify_response(response: Response) -> None:
        response.raise_for_status()

    def pop_item(self, queue_id: str) -> Task | None:
        # TODO: oci_image filter
        response = self._session.post(f"/api/v0/scheduler/queues/{queue_id}/pop", json={})
        self._verify_response(response)

        task = TypeAdapter(Task | None).validate_json(response.content)

        return task

    def pop_items(self, scheduler_id: str, filters: dict[str, Any]) -> PaginatedTasksResponse | None:
        response = self._session.post(f"/api/v0/scheduler/queues/{scheduler_id}/pop", json={
            "filters": [{"column": "data", "field": "oci_image", "operator": "eq", "value": self.oci_image}],
        })
        self._verify_response(response)

        task = TypeAdapter(PaginatedTasksResponse | None).validate_json(response.content)

        return task

    def push_item(self, p_item: Task) -> None:
        response = self._session.post(
            f"/api/v0/scheduler/queues/{p_item.scheduler_id}/push", content=p_item.model_dump_json()
        )
        self._verify_response(response)

    def patch_task(self, task_id: uuid.UUID, status: TaskStatus) -> None:
        response = self._session.patch(f"/api/v0/scheduler/tasks/{task_id}", json={"status": status.value})
        self._verify_response(response)

    def get_task(self, task_id: uuid.UUID) -> Task:
        response = self._session.get(f"/api/v0/scheduler/tasks/{task_id}")
        self._verify_response(response)

        task = Task.model_validate_json(response.content)

        return task

    def save_raws(self, boefje_meta_id: uuid.UUID, boefje_output: BoefjeOutput) -> dict[str, uuid.UUID]:
        response = self._session.post(
            f"/api/v0/tasks/{boefje_meta_id}",
            content=boefje_output.model_dump_json(),
            params={"boefje_meta_id": str(boefje_meta_id)},
        )
        self._verify_response(response)

        return response.json()
