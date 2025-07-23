from datetime import datetime, timezone
from typing import Literal

import docker
import structlog
from django.conf import settings
from django.urls import reverse
from docker.errors import APIError, ContainerError, ImageNotFound

from files.models import File, NamedContent
from katalogus.worker.interfaces import BoefjeOutput
from katalogus.worker.job_models import BoefjeMeta
from tasks.models import Task, TaskResult, TaskStatus

logger = structlog.get_logger(__name__)

MIMETYPE_MIN_LENGTH = 5  # two chars before, and 2 chars after the slash ought to be reasonable


class DockerBoefjeHandler:
    CACHE_VOLUME_NAME = "openkat_cache"
    CACHE_VOLUME_TARGET = "/home/nonroot/openkat_cache"

    def __init__(self):
        self.docker_client = docker.from_env()

    def handle(self, task: Task) -> tuple[BoefjeMeta, BoefjeOutput] | None | Literal[False]:
        """
        With regard to the return type:
            :rtype: tuple[BoefjeMeta, list[tuple[set, bytes | str]]] | None | bool

        The return type signals the app how the boefje was handled. A successful run returns a tuple of the updated
        boefje_meta and its results to allow for deduplication. A failure returns None. And for now as a temporary
        solution, we return False if the task was not handled here directly, but delegated to the Docker runner.
        """
        boefje_meta = BoefjeMeta.model_validate(task.data)

        if not boefje_meta.boefje.oci_image:
            raise RuntimeError("Boefje does not have OCI image")

        task_id = boefje_meta.id
        task.data["started_at"] = str(datetime.now(timezone.utc))

        try:
            input_url = f"{settings.OPENKAT_HOST}{reverse('boefje-input', args=(task_id,))}"
            logger.info(task.status)
            # TODO: create auth token and add it to the input/env of the container to use for its requests
            container_logs = self.docker_client.containers.run(
                image=boefje_meta.boefje.oci_image,
                name="kat_boefje_" + str(task_id),
                command=input_url,
                stdout=False,
                stderr=True,
                remove=True,
                network=settings.DOCKER_NETWORK,
                volumes=[f"{self.CACHE_VOLUME_NAME}:{self.CACHE_VOLUME_TARGET}"],
            )
            # TODO: delete the token immediately

            task.refresh_from_db(fields=["status"])

            # if the status is "RUNNING", the container didn't call the output API endpoint, so set it to "FAILED"
            if task.status == TaskStatus.RUNNING:
                task.data["ended_at"] = str(datetime.now(timezone.utc))
                task.status = TaskStatus.FAILED
                task.save()
                raw = File.objects.create(file=NamedContent(container_logs), type="boefje/error")
                TaskResult.objects.create(task=task, file=raw)

                # have to raise exception to prevent _start_working function from setting status to completed
                raise RuntimeError("Boefje did not call output API endpoint")
        except ContainerError as e:
            logger.error(
                "Container for task %s failed and returned exit status %d, stderr saved to bytes",
                task_id,
                e.exit_status,
            )
            task.data["ended_at"] = str(datetime.now(timezone.utc))
            task.status = TaskStatus.FAILED
            task.save()
            raw = File.objects.create(
                file=NamedContent(e.stderr if isinstance(e.stderr, bytes) else e.stderr.encode()), type="boefje/error"
            )
            TaskResult.objects.create(task=task, file=raw)
        except ImageNotFound:
            logger.error("Docker image %s not found", boefje_meta.boefje.oci_image)
            task.data["ended_at"] = str(datetime.now(timezone.utc))
            task.status = TaskStatus.FAILED
            task.save()
        except APIError as e:
            logger.error("Docker API error: %s", e)
            task.data["ended_at"] = str(datetime.now(timezone.utc))
            task.status = TaskStatus.FAILED
            task.save()

        return False
