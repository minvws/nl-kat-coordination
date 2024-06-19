import logging
from datetime import datetime, timezone

import httpx
from httpx import Timeout
from pydantic import BaseModel

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.clients.scheduler_client import SchedulerAPIClient, TaskStatus
from boefjes.config import settings
from boefjes.job_models import BoefjeMeta
from boefjes.katalogus.models import Boefje

logger = logging.getLogger(__name__)


class RemoteBoefjesRunner:
    def __init__(self, boefje_resource: Boefje, boefje_meta: BoefjeMeta):
        self.boefje_resource = boefje_resource
        self.boefje_meta = boefje_meta
        self.scheduler_client = SchedulerAPIClient(str(settings.scheduler_api))
        self.bytes_api_client = BytesAPIClient(
            str(settings.bytes_api),
            username=settings.bytes_username,
            password=settings.bytes_password,
        )

    def run(self) -> None:
        remote_url = self.boefje_meta.environment.get("remote_url", "")
        if not remote_url:
            raise RuntimeError("Boefje does not have a URL")

        # local import to prevent circular dependency
        import boefjes.plugins.models  # TODO: ask why this is needed since boefjes.plugins.models gets imported on top

        stderr_mime_types = boefjes.plugins.models._default_mime_types(self.boefje_meta.boefje)

        task_id = self.boefje_meta.id
        self.scheduler_client.patch_task(task_id, TaskStatus.RUNNING)  # TODO: do this inside remote boefje
        self.boefje_meta.started_at = datetime.now(timezone.utc)

        try:
            task_url = str(settings.api).rstrip("/") + f"/api/v0/tasks/{task_id}"

            request = RemoteBoefjeRequest(
                name="kat_boefje_" + str(task_id),
                task_url=task_url,
                boefje_resource=self.boefje_resource,
                boefje_meta=self.boefje_meta,
            )

            response = httpx.post(
                url=self.boefje_resource.remote_url, content=request.model_dump_json(), timeout=Timeout(timeout=10)
            )

            if response.is_error:
                self.boefje_meta.ended_at = datetime.now(timezone.utc)
                self.bytes_api_client.save_boefje_meta(self.boefje_meta)  # The task didn't create a boefje_meta object
                self.bytes_api_client.save_raw(task_id, response, stderr_mime_types.union({"error/boefje"}))
                self.scheduler_client.patch_task(task_id, TaskStatus.FAILED)

                # have to raise exception to prevent _start_working function from setting status to completed
                raise RuntimeError("Boefje did not call output API endpoint")

        except httpx.NetworkError as e:
            logger.exception("Container error")

            # save container log (stderr) to bytes
            self.bytes_api_client.login()
            self.boefje_meta.ended_at = datetime.now(timezone.utc)
            try:
                # this boefje_meta might be incomplete, it comes from the scheduler instead of the Boefje I/O API
                self.bytes_api_client.save_boefje_meta(self.boefje_meta)
            except httpx.HTTPError:
                logger.error("Failed to save boefje meta to bytes, continuing anyway")
            self.bytes_api_client.save_raw(task_id, "TODO", stderr_mime_types)  # TODO
            self.scheduler_client.patch_task(task_id, TaskStatus.FAILED)
            # have to raise exception to prevent _start_working function from setting status to completed
            raise e


class RemoteBoefjeRequest(BaseModel):
    name: str
    task_url: str
    boefje_resource: Boefje
    boefje_meta: BoefjeMeta
