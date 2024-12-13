import base64
import multiprocessing
import uuid
from datetime import datetime, timezone
from multiprocessing.context import ForkContext, ForkProcess
from uuid import UUID

import structlog
from fastapi import Depends, FastAPI, HTTPException, Response
from httpx import HTTPError, HTTPStatusError
from pydantic import BaseModel, ConfigDict
from uvicorn import Config, Server

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.clients.scheduler_client import SchedulerAPIClient
from boefjes.config import settings
from boefjes.dependencies.plugins import get_plugin_service
from boefjes.worker.job_models import BoefjeMeta
from boefjes.worker.repository import _default_mime_types
from boefjes.worker.interfaces import TaskStatus, StatusEnum, BoefjeOutput, Queue, Task

app = FastAPI(title="Boefje API")
logger = structlog.get_logger(__name__)
ctx: ForkContext = multiprocessing.get_context("fork")


class UvicornServer(ForkProcess):
    def __init__(self, config: Config):
        super().__init__()
        self.server = Server(config=config)
        self.config = config

    def stop(self) -> None:
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


def get_scheduler_client(plugin_service=Depends(get_plugin_service)):
    return SchedulerAPIClient(plugin_service, str(settings.scheduler_api))


def get_bytes_client():
    return BytesAPIClient(str(settings.bytes_api), username=settings.bytes_username, password=settings.bytes_password)


@app.get("/healthz")
async def root():
    return "OK"


@app.get("/api/v0/tasks/{task_id}", response_model=BoefjeInput)
def boefje_input(task_id: UUID, scheduler_client: SchedulerAPIClient = Depends(get_scheduler_client)) -> BoefjeInput:
    task = get_task(task_id, scheduler_client)

    if task.status is not TaskStatus.RUNNING:
        raise HTTPException(status_code=403, detail="Task does not have status running")

    output_url = str(settings.api).rstrip("/") + f"/api/v0/tasks/{task_id}"
    return BoefjeInput(task_id=task_id, output_url=output_url, boefje_meta=task.data)


@app.post("/api/v0/tasks/{task_id}")
def boefje_output(
    task_id: UUID,
    boefje_output: BoefjeOutput,
    scheduler_client: SchedulerAPIClient = Depends(get_scheduler_client),
    bytes_client: BytesAPIClient = Depends(get_bytes_client),
) -> Response:
    task = get_task(task_id, scheduler_client)
    boefje_meta = task.data

    if task.status is not TaskStatus.RUNNING:
        raise HTTPException(status_code=403, detail="Task does not have status running")

    boefje_meta.started_at = task.modified_at
    boefje_meta.ended_at = datetime.now(timezone.utc)

    bytes_client.login()
    bytes_client.save_boefje_meta(boefje_meta)

    if boefje_output.files:
        mime_types = _default_mime_types(boefje_meta.boefje)
        for file in boefje_output.files:
            file.tags = mime_types.union(file.tags) if file.tags else mime_types

        # when supported, also save file.name to Bytes
        bytes_client.save_raws(task_id, boefje_output)

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


# The "scheduler proxy" endpoints

@app.get("/api/v0/scheduler/queues", response_model=list[Queue], tags=["scheduler"])
def get_queues(scheduler_client: SchedulerAPIClient = Depends(get_scheduler_client)) -> list[Queue]:
    return scheduler_client.get_queues()


@app.get("/api/v0/scheduler/queues/{queue_id}/pop", response_model=Task | None, tags=["scheduler"])
def pop_task(queue_id: str, scheduler_client: SchedulerAPIClient = Depends(get_scheduler_client)) -> Task | None:
    return scheduler_client.pop_item(queue_id)


@app.post("/api/v0/scheduler/queues/{queue_id}/push", tags=["scheduler"])
def push_item(queue_id: str, p_item: Task, scheduler_client: SchedulerAPIClient = Depends(get_scheduler_client)) -> None:
    return scheduler_client.push_item(p_item)


@app.patch("/api/v0/scheduler/tasks/{task_id}", tags=["scheduler"])
def patch_task(task_id: uuid.UUID, status: TaskStatus, scheduler_client: SchedulerAPIClient = Depends(get_scheduler_client)) -> None:
    return scheduler_client.patch_task(task_id, status)


@app.get("/api/v0/scheduler/tasks/{task_id}", response_model=Task, tags=["scheduler"])
def get_task(task_id: uuid.UUID, scheduler_client: SchedulerAPIClient = Depends(get_scheduler_client)) -> Task:
    return scheduler_client.get_task(task_id)
