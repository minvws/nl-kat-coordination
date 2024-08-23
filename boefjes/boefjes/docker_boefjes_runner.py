from datetime import datetime, timezone

import docker
import structlog
from docker.errors import APIError, ContainerError, ImageNotFound
from httpx import HTTPError

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.clients.scheduler_client import SchedulerAPIClient, TaskStatus
from boefjes.config import settings
from boefjes.job_models import BoefjeMeta
from boefjes.models import Boefje

logger = structlog.get_logger(__name__)


class DockerBoefjesRunner:
    def __init__(self, boefje_resource: Boefje, boefje_meta: BoefjeMeta):
        self.boefje_resource = boefje_resource
        self.boefje_meta = boefje_meta
        self.docker_client = docker.from_env()
        self.scheduler_client = SchedulerAPIClient(str(settings.scheduler_api))
        self.bytes_api_client = BytesAPIClient(
            str(settings.bytes_api),
            username=settings.bytes_username,
            password=settings.bytes_password,
        )

    def run(self) -> None:
        if not self.boefje_resource.oci_image:
            raise RuntimeError("Boefje does not have OCI image")

        # local import to prevent circular dependency
        import boefjes.plugins.models

        stderr_mime_types = boefjes.plugins.models._default_mime_types(self.boefje_meta.boefje)

        task_id = self.boefje_meta.id
        self.scheduler_client.patch_task(task_id, TaskStatus.RUNNING)
        self.boefje_meta.started_at = datetime.now(timezone.utc)

        try:
            input_url = str(settings.api).rstrip("/") + f"/api/v0/tasks/{task_id}"
            container_logs = self.docker_client.containers.run(
                image=self.boefje_resource.oci_image,
                name="kat_boefje_" + str(task_id),
                command=input_url,
                stdout=False,
                stderr=True,
                remove=True,
                network=settings.docker_network,
            )

            task = self.scheduler_client.get_task(task_id)

            # if status is still running the container didn't call the output API endpoint, so set to status to failed
            if task.status == TaskStatus.RUNNING:
                self.boefje_meta.ended_at = datetime.now(timezone.utc)
                self.bytes_api_client.save_boefje_meta(self.boefje_meta)  # The task didn't create a boefje_meta object
                self.bytes_api_client.save_raw(task_id, container_logs, stderr_mime_types.union({"error/boefje"}))
                self.scheduler_client.patch_task(task_id, TaskStatus.FAILED)

                # have to raise exception to prevent _start_working function from setting status to completed
                raise RuntimeError("Boefje did not call output API endpoint")
        except ContainerError as e:
            logger.exception("Container error")

            # save container log (stderr) to bytes
            self.bytes_api_client.login()
            self.boefje_meta.ended_at = datetime.now(timezone.utc)
            try:
                # this boefje_meta might be incomplete, it comes from the scheduler instead of the Boefje I/O API
                self.bytes_api_client.save_boefje_meta(self.boefje_meta)
            except HTTPError:
                logger.error("Failed to save boefje meta to bytes, continuing anyway")
            self.bytes_api_client.save_raw(task_id, e.stderr, stderr_mime_types)
            self.scheduler_client.patch_task(task_id, TaskStatus.FAILED)
            # have to raise exception to prevent _start_working function from setting status to completed
            raise e
        except (APIError, ImageNotFound) as e:
            logger.exception("API error or image not found")
            self.scheduler_client.patch_task(task_id, TaskStatus.FAILED)
            raise e
