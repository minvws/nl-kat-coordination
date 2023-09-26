import base64
import logging
import multiprocessing
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Extra, Field
from requests import HTTPError
from uvicorn import Config, Server

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.clients.scheduler_client import SchedulerAPIClient, TaskStatus
from boefjes.config import settings
from boefjes.job_handler import (
    _collect_default_mime_types,
    _find_ooi_in_past,
    get_environment_settings,
    get_octopoes_api_connector,
    serialize_ooi,
)
from boefjes.job_models import BoefjeMeta
from boefjes.katalogus.local_repository import get_local_repository
from octopoes.models import Reference

app = FastAPI()
logger = logging.getLogger(__name__)
local_repository = get_local_repository()
scheduler_client = SchedulerAPIClient(settings.scheduler_api)
bytes_api_client = BytesAPIClient(
    settings.bytes_api,
    username=settings.bytes_username,
    password=settings.bytes_password,
)


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
    config = Config(app, host=settings.boefje_api_host, port=settings.boefje_api_port)
    instance = UvicornServer(config=config)
    instance.start()
    return instance


class BoefjeInput(BaseModel):
    task_id: str
    output_url: str
    boefje_meta: BoefjeMeta

    class Config:
        extra = Extra.forbid


class StatusEnum(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class File(BaseModel):
    name: Optional[str]
    content: str = Field(..., contentEncoding="base64")
    tags: Optional[List[str]]


class BoefjeOutput(BaseModel):
    status: StatusEnum
    files: Optional[List[File]]


@app.get("/healthz")
async def root():
    return "OK"


@app.get("/api/v0/tasks/{task_id}", response_model=BoefjeInput)
async def boefje_input(task_id: str):
    task = get_task(task_id)

    if task.status is not TaskStatus.RUNNING:
        raise HTTPException(status_code=403, detail="Task does not have status running")

    boefje_meta = create_boefje_meta(task)

    output_url = settings.boefje_api + "/api/v0/tasks/" + task_id
    return BoefjeInput(task_id=task_id, output_url=output_url, boefje_meta=boefje_meta)


@app.post("/api/v0/tasks/{task_id}")
async def boefje_output(task_id: str, boefje_output: BoefjeOutput):
    task = get_task(task_id)

    if task.status is not TaskStatus.RUNNING:
        raise HTTPException(status_code=403, detail="Task does not have status running")

    boefje_meta = create_boefje_meta(task)
    boefje_meta.started_at = task.modified_at
    boefje_meta.ended_at = datetime.now(timezone.utc)

    bytes_api_client.login()
    bytes_api_client.save_boefje_meta(boefje_meta)

    if boefje_output.files:
        mime_types = _collect_default_mime_types(task.p_item.data)
        for file in boefje_output.files:
            raw = base64.b64decode(file.content)
            # when supported, also save file.name to Bytes
            bytes_api_client.save_raw(task_id, raw, mime_types.union(file.tags))

    if boefje_output.status == StatusEnum.COMPLETED:
        scheduler_client.patch_task(task_id, TaskStatus.COMPLETED)
    elif boefje_output.status == StatusEnum.FAILED:
        scheduler_client.patch_task(task_id, TaskStatus.FAILED)

    return Response(status_code=200)


def get_task(task_id):
    try:
        task = scheduler_client.get_task(task_id)
    except HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Task not found")
        else:
            logger.exception("Failed to get task from scheduler")
            raise HTTPException(status_code=500, detail="Internal server error")
    return task


def create_boefje_meta(task):
    boefje = task.p_item.data.boefje
    boefje_resource = local_repository.by_id(boefje.id)
    env_keys = boefje_resource.environment_keys
    environment = get_environment_settings(task.p_item.data, env_keys) if env_keys else {}

    organization = task.p_item.data.organization
    input_ooi = task.p_item.data.input_ooi
    arguments = {}
    if input_ooi:
        arguments["input"] = serialize_ooi(
            _find_ooi_in_past(
                Reference.from_str(input_ooi),
                get_octopoes_api_connector(organization),
            )
        )

    boefje_meta = BoefjeMeta(
        id=task.id,
        boefje=boefje,
        input_ooi=input_ooi,
        arguments=arguments,
        organization=organization,
        environment=environment,
    )
    return boefje_meta
