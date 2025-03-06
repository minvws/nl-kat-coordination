import os

import structlog

from .interfaces import JobRuntimeError
from .job_models import BoefjeMeta
from .repository import LocalPluginRepository

logger = structlog.get_logger(__name__)


class TemporaryEnvironment:
    """Context manager that temporarily clears the environment vars and restores it after exiting the context"""

    def __init__(self):
        self._original_environment = os.environ.copy()

    def __enter__(self):
        os.environ.clear()
        return os.environ

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.environ.clear()
        os.environ.update(self._original_environment)


class LocalBoefjeJobRunner:
    def __init__(self, local_repository: LocalPluginRepository):
        self.local_repository = local_repository

    def run(self, boefje_meta: BoefjeMeta, environment: dict[str, str]) -> list[tuple[set, bytes | str]]:
        logger.debug("Running local boefje plugin")

        boefjes = self.local_repository.resolve_boefjes()
        boefje_resource = boefjes[boefje_meta.boefje.id]

        if not boefje_resource.module:
            if boefje_resource.boefje.oci_image:
                raise JobRuntimeError("Trying to run OCI image boefje locally")
            else:
                raise JobRuntimeError("Boefje doesn't have OCI image or main.py")

        with TemporaryEnvironment() as temporary_environment:
            temporary_environment.update(environment)
            try:
                return boefje_resource.module.run(boefje_meta)
            except BaseException as e:  # noqa
                raise JobRuntimeError("Boefje failed") from e
