import os
import traceback
from base64 import b64encode

import structlog

from .interfaces import BoefjeOutput, BoefjeStorageInterface, File, Handler, StatusEnum, Task, JobRuntimeError
from .job_models import BoefjeMeta
from .repository import LocalPluginRepository, BoefjeResource, _default_mime_types

logger = structlog.get_logger(__name__)

MIMETYPE_MIN_LENGTH = 5  # two chars before, and 2 chars after the slash ought to be reasonable



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


class BoefjeHandler(Handler):
    def __init__(self, local_repository: LocalPluginRepository, boefje_storage: BoefjeStorageInterface):
        self.local_repository = local_repository
        self.boefje_storage = boefje_storage

    def handle(self, task: Task) -> None:
        boefje_meta = task.data

        if not isinstance(boefje_meta, BoefjeMeta):
            raise ValueError("Plugin id does not belong to a boefje")

        logger.info("Starting boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))

        boefje_results: list[tuple[set, bytes | str]] = []
        failed = False

        try:
            logger.debug("Running local boefje plugin")

            boefje_resource = self.local_repository.by_id(boefje_meta.boefje.id)  # TODO: by image?

            if not isinstance(boefje_resource, BoefjeResource):
                raise JobRuntimeError(f"Not a boefje: {boefje_meta.boefje.id}")

            if not boefje_resource.module:
                raise JobRuntimeError(f"Not runnable module found")

            with TemporaryEnvironment() as temporary_environment:
                temporary_environment.update(boefje_meta.environment or {})
                try:
                    boefje_results = boefje_resource.module.run(boefje_meta.model_dump())
                except BaseException as e:  # noqa
                    raise JobRuntimeError("Boefje failed") from e
        except:
            logger.exception("Error running boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))
            boefje_results = [({"error/boefje"}, traceback.format_exc())]
            failed = True

            raise
        finally:
            logger.info("Saving to Bytes for boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))

            if not boefje_results:
                logger.info("No results for boefje %s[%s]", boefje_meta.boefje.id, boefje_meta.id)
                return None

            files = []

            for boefje_added_mime_types, output in boefje_results:
                valid_mimetypes = set()
                for mimetype in boefje_added_mime_types:
                    if len(mimetype) < MIMETYPE_MIN_LENGTH or "/" not in mimetype:
                        logger.warning(
                            "Invalid mime-type encountered in output for boefje %s[%s]",
                            boefje_meta.boefje.id,
                            str(boefje_meta.id),
                        )
                    else:
                        valid_mimetypes.add(mimetype)

                files.append(
                    File(
                        name=str(len(files)),
                        content=(
                            b64encode(output) if isinstance(output, bytes) else b64encode(output.encode())
                        ).decode(),
                        tags=_default_mime_types(boefje_meta.boefje).union(valid_mimetypes),  # default mime-types are added through the API
                    )
                )

            boefje_output = BoefjeOutput(status=StatusEnum.FAILED if failed else StatusEnum.COMPLETED, files=files)
            raw_file_ids = self.boefje_storage.save_raws(boefje_meta.id, boefje_output)

            logger.info(
                "Saved %s raw files for boefje %s[%s]", len(raw_file_ids), boefje_meta.boefje.id, boefje_meta.id
            )
