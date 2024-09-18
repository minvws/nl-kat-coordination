import base64
import multiprocessing
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

import structlog
from fastapi import Depends, FastAPI, HTTPException, Response
from httpx import HTTPError, HTTPStatusError
from pydantic import BaseModel, ConfigDict, Field
from uvicorn import Config, Server

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.clients.scheduler_client import SchedulerAPIClient, TaskStatus
from boefjes.config import settings
from boefjes.dependencies.plugins import PluginService, get_plugin_service
from boefjes.job_handler import get_environment_settings, get_octopoes_api_connector
from boefjes.job_models import BoefjeMeta
from boefjes.models import PluginType
from boefjes.plugins.models import _default_mime_types
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException

app = FastAPI(title="Boefje API")
logger = structlog.get_logger(__name__)


class UvicornServer(multiprocessing.Process):
    def __init__(self, config: Config):
        super().__init__()
        self.server = Server(config=config)
        self.config = config

    def stop(self):
        self.terminate()

    def run(self, *args, **kwargs):
        self.server.run()


def run():
    config = Config(app, host=settings.api_host, port=settings.api_port)
    instance = UvicornServer(config=config)
    instance.start()
    return instance


class BoefjeInput(BaseModel):
    task_id: UUID
    output_url: str
    boefje_meta: BoefjeMeta
    model_config = ConfigDict(extra="forbid")


class StatusEnum(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class File(BaseModel):
    name: str | None = None
    content: str = Field(json_schema_extra={"contentEncoding": "base64"})
    tags: list[str] | None = None


class BoefjeOutput(BaseModel):
    status: StatusEnum
    files: list[File] | None = None


def get_scheduler_client():
    return SchedulerAPIClient(str(settings.scheduler_api))


def get_bytes_client():
    return BytesAPIClient(
        str(settings.bytes_api),
        username=settings.bytes_username,
        password=settings.bytes_password,
    )


@app.get("/healthz")
async def root():
    return "OK"


@app.get("/api/v0/tasks/{task_id}", response_model=BoefjeInput)
def boefje_input(
    task_id: UUID,
    scheduler_client: SchedulerAPIClient = Depends(get_scheduler_client),
    plugin_service: PluginService = Depends(get_plugin_service),
):
    task = get_task(task_id, scheduler_client)

    if task.status is not TaskStatus.RUNNING:
        raise HTTPException(status_code=403, detail="Task does not have status running")

    plugin = plugin_service.by_plugin_id(task.data.boefje.id, task.data.organization)
    boefje_meta = create_boefje_meta(task, plugin)

    output_url = str(settings.api).rstrip("/") + f"/api/v0/tasks/{task_id}"
    return BoefjeInput(task_id=task_id, output_url=output_url, boefje_meta=boefje_meta)


@app.post("/api/v0/tasks/{task_id}")
def boefje_output(
    task_id: UUID,
    boefje_output: BoefjeOutput,
    scheduler_client: SchedulerAPIClient = Depends(get_scheduler_client),
    bytes_client: BytesAPIClient = Depends(get_bytes_client),
    plugin_service: PluginService = Depends(get_plugin_service),
):
    task = get_task(task_id, scheduler_client)

    if task.status is not TaskStatus.RUNNING:
        raise HTTPException(status_code=403, detail="Task does not have status running")

    plugin = plugin_service.by_plugin_id(task.data.boefje.id, task.data.organization)
    boefje_meta = create_boefje_meta(task, plugin)
    boefje_meta.started_at = task.modified_at
    boefje_meta.ended_at = datetime.now(timezone.utc)

    bytes_client.login()
    bytes_client.save_boefje_meta(boefje_meta)

    if boefje_output.files:
        mime_types = _default_mime_types(boefje_meta.boefje).union(plugin.produces)
        for file in boefje_output.files:
            raw = base64.b64decode(file.content)
            # when supported, also save file.name to Bytes
            bytes_client.save_raw(task_id, raw, mime_types.union(file.tags))

    if boefje_output.status == StatusEnum.COMPLETED:
        scheduler_client.patch_task(task_id, TaskStatus.COMPLETED)
    elif boefje_output.status == StatusEnum.FAILED:
        scheduler_client.patch_task(task_id, TaskStatus.FAILED)

    return Response(status_code=200)


def get_task(task_id, scheduler_client):
    try:
        task = scheduler_client.get_task(task_id)
    except HTTPError as e:
        if isinstance(e, HTTPStatusError) and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Task not found")
        else:
            logger.exception("Failed to get task from scheduler")
            raise HTTPException(status_code=500, detail="Internal server error")
    return task


def create_boefje_meta(task, plugin: PluginType) -> BoefjeMeta:
    organization = task.data.organization
    input_ooi = task.data.input_ooi
    arguments = {"oci_arguments": plugin.oci_arguments}

    if input_ooi:
        reference = Reference.from_str(input_ooi)
        try:
            ooi = get_octopoes_api_connector(organization).get(reference, valid_time=datetime.now(timezone.utc))
        except ObjectNotFoundException as e:
            raise ObjectNotFoundException(f"Object {reference} not found in Octopoes") from e

        arguments["input"] = ooi.serialize()

    boefje_meta = BoefjeMeta(
        id=task.id,
        boefje=task.data.boefje,
        input_ooi=input_ooi,
        arguments=arguments,
        organization=organization,
        environment=get_environment_settings(task.data, plugin.schema),
    )
    return boefje_meta
