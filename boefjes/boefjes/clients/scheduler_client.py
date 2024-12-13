import datetime
import os
import uuid

import httpx
import structlog
from httpx import Client, HTTPError, HTTPTransport, Response
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate
from pydantic import TypeAdapter

from boefjes.config import settings
from boefjes.dependencies.plugins import PluginService
from boefjes.worker.interfaces import Queue, SchedulerClientInterface, Task, TaskStatus
from boefjes.worker.job_models import BoefjeMeta
from boefjes.storage.interfaces import SettingsNotConformingToSchema
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException

logger = structlog.get_logger(__name__)


class SchedulerAPIClient(SchedulerClientInterface):
    def __init__(self, plugin_service: PluginService, base_url: str):
        self._session = Client(base_url=base_url, transport=HTTPTransport(retries=6), timeout=settings.outgoing_request_timeout)
        self.plugin_service = plugin_service

    @staticmethod
    def _verify_response(response: Response) -> None:
        response.raise_for_status()

    def get_queues(self) -> list[Queue]:
        response = self._session.get("/queues")
        self._verify_response(response)

        return TypeAdapter(list[Queue]).validate_json(response.content)

    def pop_item(self, queue_id: str) -> Task | None:
        response = self._session.post(f"/queues/{queue_id}/pop")
        self._verify_response(response)

        task = TypeAdapter(Task | None).validate_json(response.content)

        if not task:
            return None

        if isinstance(task.data, BoefjeMeta):
            task.data = self._hydrate_boefje_meta(task.data)

        return task

    def push_item(self, p_item: Task) -> None:
        response = self._session.post(f"/queues/{p_item.scheduler_id}/push", content=p_item.model_dump_json())
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
    new_env = {
        key.split("BOEFJE_", 1)[1]: value
        for key, value in os.environ.items()
        if key.startswith("BOEFJE_") and key in allowed_keys
    }

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
