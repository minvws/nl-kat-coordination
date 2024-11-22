from datetime import datetime, timezone

import docker
import structlog
from docker.errors import APIError, ContainerError, ImageNotFound
from httpx import HTTPError

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.clients.scheduler_client import SchedulerAPIClient
from boefjes.config import settings
from boefjes.interfaces import Task, TaskStatus

logger = structlog.get_logger(__name__)


class DockerBoefjesRunner:
    CACHE_VOLUME_NAME = "openkat_cache"
    CACHE_VOLUME_TARGET = "/home/nonroot/openkat_cache"

    def __init__(self, scheduler_client: SchedulerAPIClient, bytes_api_client: BytesAPIClient):
        self.docker_client = docker.from_env()
        self.scheduler_client = scheduler_client
        self.bytes_api_client = bytes_api_client

    def run(self, task: Task) -> None:
        boefje_meta = task.data
        oci_image = boefje_meta.arguments["oci_image"]

        if not oci_image:
            raise RuntimeError("Boefje does not have OCI image")

        # local import to prevent circular dependency
        import boefjes.plugins.models

        stderr_mime_types = boefjes.plugins.models._default_mime_types(boefje_meta.boefje)

        task_id = boefje_meta.id
        boefje_meta.started_at = datetime.now(timezone.utc)

        try:
            input_url = str(settings.api).rstrip("/") + f"/api/v0/tasks/{task_id}"
            container_logs = self.docker_client.containers.run(
                image=oci_image,
                name="kat_boefje_" + str(task_id),
                command=input_url,
                stdout=False,
                stderr=True,
                remove=True,
                network=settings.docker_network,
                volumes=[f"{self.CACHE_VOLUME_NAME}:{self.CACHE_VOLUME_TARGET}"],
            )

            task = self.scheduler_client.get_task(task_id)

            # if status is still running the container didn't call the output API endpoint, so set to status to failed
            if task.status == TaskStatus.RUNNING:
                boefje_meta.ended_at = datetime.now(timezone.utc)
                self.bytes_api_client.save_boefje_meta(boefje_meta)  # The task didn't create a boefje_meta object
                self.bytes_api_client.save_raw(task_id, container_logs, stderr_mime_types.union({"error/boefje"}))
                self.scheduler_client.patch_task(task_id, TaskStatus.FAILED)

                # have to raise exception to prevent _start_working function from setting status to completed
                raise RuntimeError("Boefje did not call output API endpoint")
        except ContainerError as e:
            logger.error(
                "Container for task %s failed and returned exit status %d, stderr saved to bytes",
                task_id,
                e.exit_status,
            )

            # save container log (stderr) to bytes
            self.bytes_api_client.login()
            boefje_meta.ended_at = datetime.now(timezone.utc)
            try:
                # this boefje_meta might be incomplete, it comes from the scheduler instead of the Boefje I/O API
                self.bytes_api_client.save_boefje_meta(boefje_meta)
            except HTTPError:
                logger.error("Failed to save boefje meta to bytes, continuing anyway")
            self.bytes_api_client.save_raw(task_id, e.stderr, stderr_mime_types)
            self.scheduler_client.patch_task(task_id, TaskStatus.FAILED)
        except ImageNotFound:
            logger.error("Docker image %s not found", oci_image)
            self.scheduler_client.patch_task(task_id, TaskStatus.FAILED)
        except APIError as e:
            logger.error("Docker API error: %s", e)
            self.scheduler_client.patch_task(task_id, TaskStatus.FAILED)
