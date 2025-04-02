import uuid
from typing import Any

from httpx import Client, HTTPTransport, Response
from pydantic import TypeAdapter

# A deliberate relative import to make this module self-contained
from .interfaces import (
    BoefjeOutput,
    BoefjeStorageInterface,
    PaginatedTasksResponse,
    SchedulerClientInterface,
    Task,
    TaskStatus,
)


class BoefjeAPIClient(SchedulerClientInterface, BoefjeStorageInterface):
    def __init__(self, base_url: str, outgoing_request_timeout: int, oci_images: list[str] | None = None, plugins: list[str] | None = None):
        self._session = Client(base_url=base_url, transport=HTTPTransport(retries=6), timeout=outgoing_request_timeout)
        self.oci_images = oci_images
        self.plugins = plugins

    @staticmethod
    def _verify_response(response: Response) -> None:
        response.raise_for_status()

    def pop_item(self, queue_id: str) -> Task | None:
        page = self.pop_items(queue_id, limit=1)

        if not page or page.count == 0:
            return None

        return page.results[0]

    def pop_items(self, queue_id: str, filters: dict[str, list[dict[str, Any]]] | None = None, limit: int = 1) -> PaginatedTasksResponse | None:
        if not filters:
            filters = {"filters": []}
        if self.oci_images:
            filters["filters"].append({"column": "data", "field": "boefje__oci_image", "operator": "in", "value": self.oci_images})
        if self.plugins:
            filters["filters"].append({"column": "data", "field": "boefje__id", "operator": "in", "value": self.plugins})

        response = self._session.post(
            f"/api/v0/scheduler/queues/{queue_id}/pop",
            json=filters if filters["filters"] else None,
            params={"limit": limit},
        )
        self._verify_response(response)

        return TypeAdapter(PaginatedTasksResponse | None).validate_json(response.content)

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
        )
        self._verify_response(response)

        return response.json()
