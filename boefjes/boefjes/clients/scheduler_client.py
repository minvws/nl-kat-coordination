import datetime
import os
import uuid
from functools import cache
from typing import Any

import httpx
import structlog
from httpx import Client, HTTPError, HTTPTransport, Response
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate
from pydantic import BaseModel, TypeAdapter

from boefjes.config import settings
from boefjes.dependencies.plugins import PluginService
from boefjes.storage.interfaces import SettingsNotConformingToSchema
from boefjes.worker.interfaces import Queue, Task, TaskStatus
from boefjes.worker.job_models import BoefjeMeta
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException

logger = structlog.get_logger(__name__)


# TODO: refactor to models file
class PaginatedTasksResponse(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[Task]


class SchedulerClientInterface:
    def get_queues(self) -> list[Queue]:
        raise NotImplementedError()

    def pop_item(self, scheduler_id: str) -> Task | None:
        raise NotImplementedError()

    def pop_items(self, scheduler_id: str, filters: dict[str, Any]) -> PaginatedTasksResponse | None:
        raise NotImplementedError()


class SchedulerAPIClient(SchedulerClientInterface):
    def __init__(self, plugin_service: PluginService, base_url: str):
        self._session = Client(
            base_url=base_url, transport=HTTPTransport(retries=6), timeout=settings.outgoing_request_timeout
        )
        self.plugin_service = plugin_service

    @staticmethod
    def _verify_response(response: Response) -> None:
        response.raise_for_status()

    def pop_item(self, scheduler_id: str) -> Task | None:
        response = self._session.post(f"/schedulers/{scheduler_id}/pop", params={"limit": 1})
        self._verify_response(response)

        page = TypeAdapter(PaginatedTasksResponse | None).validate_json(response.content)
        if page.count == 0:
            return None

        task = page.results[0]
        if not task:
            return None

        if isinstance(task.data, BoefjeMeta):
            task.data = self._hydrate_boefje_meta(task.data)

        return task

    def pop_items(self, scheduler_id: str, filters: dict[str, Any]) -> PaginatedTasksResponse | None:
        response = self._session.post(f"/schedulers/{scheduler_id}/pop", json=filters)
        self._verify_response(response)

        return TypeAdapter(PaginatedTasksResponse | None).validate_json(response.content)

    def push_item(self, p_item: Task) -> None:
        response = self._session.post(f"/schedulers/{p_item.scheduler_id}/push", content=p_item.model_dump_json())
        self._verify_response(response)

    def patch_task(self, task_id: uuid.UUID, status: TaskStatus) -> None:
        response = self._session.patch(f"/tasks/{task_id}", json={"status": status.value})
        self._verify_response(response)

    def get_task(self, task_id: uuid.UUID) -> Task:
        response = self._session.get(f"/tasks/{task_id}")
        self._verify_response(response)

        task = Task.model_validate_json(response.content)

        if isinstance(task.data, BoefjeMeta):
            task.data = self._hydrate_boefje_meta(task.data)

        return task

    def _hydrate_boefje_meta(self, boefje_meta: BoefjeMeta) -> BoefjeMeta:
        plugin = self.plugin_service.by_plugin_id(boefje_meta.boefje.id, boefje_meta.organization)

        # The octopoes API connector is organization-specific, where the client is generic.
        octopoes_api_connector = get_octopoes_api_connector(boefje_meta.organization)
        input_ooi = boefje_meta.input_ooi
        boefje_meta.arguments = {"oci_image": plugin.oci_image, "oci_arguments": plugin.oci_arguments}
        boefje_meta.runnable_hash = plugin.runnable_hash

        if input_ooi:
            reference = Reference.from_str(input_ooi)
            try:
                ooi = octopoes_api_connector.get(reference, valid_time=datetime.datetime.now(datetime.timezone.utc))
                boefje_meta.arguments["input"] = ooi.serialize()
            except ObjectNotFoundException:
                logger.info(
                    "Can't run boefje because OOI does not exist anymore [reference=%s]",
                    reference,
                    boefje_id=boefje_meta.boefje.id,
                    ooi=boefje_meta.input_ooi,
                    task_id=boefje_meta.id,
                )
                raise

        boefje_meta.environment = get_environment_settings(boefje_meta, plugin.boefje_schema)

        return boefje_meta


@cache
def boefje_env_variables() -> dict:
    """
    Return all environment variables that start with BOEFJE_. The returned
    keys have the BOEFJE_ prefix removed.
    """

    boefje_variables = {}
    for key, value in os.environ.items():
        if key.startswith("BOEFJE_"):
            boefje_variables[key.removeprefix("BOEFJE_")] = value

    return boefje_variables


def get_system_env_settings_for_boefje(allowed_keys: list[str]) -> dict:
    return {key: value for key, value in boefje_env_variables().items() if key in allowed_keys}


def get_environment_settings(boefje_meta: BoefjeMeta, schema: dict | None = None) -> dict[str, str]:
    try:
        katalogus_api = str(settings.katalogus_api).rstrip("/")
        response = httpx.get(
            f"{katalogus_api}/v1/organisations/{boefje_meta.organization}/{boefje_meta.boefje.id}/settings", timeout=30
        )
        response.raise_for_status()
    except HTTPError:
        logger.exception("Error getting environment settings")
        raise

    allowed_keys = schema.get("properties", []) if schema else []
    new_env = get_system_env_settings_for_boefje(allowed_keys)

    settings_from_katalogus = response.json()

    for key, value in settings_from_katalogus.items():
        if key in allowed_keys:
            new_env[key] = value

    # The schema, besides dictating that a boefje cannot run if it is not matched, also provides an extra safeguard:
    # it is possible to inject code if arguments are passed that "escape" the call to a tool. Hence, we should enforce
    # the schema somewhere and make the schema as strict as possible.
    if schema is not None:
        try:
            validate(instance=new_env, schema=schema)
        except ValidationError as e:
            raise SettingsNotConformingToSchema(boefje_meta.boefje.id, e.message) from e

    return new_env


def get_octopoes_api_connector(org_code: str) -> OctopoesAPIConnector:
    return OctopoesAPIConnector(str(settings.octopoes_api), org_code)
