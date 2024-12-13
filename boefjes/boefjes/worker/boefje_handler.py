import traceback
from datetime import datetime, timezone

import structlog

from .interfaces import Handler, Task, BoefjeStorageInterface
from .job_models import BoefjeMeta, Boefje
from ..local.local import LocalBoefjeJobRunner

logger = structlog.get_logger(__name__)

MIMETYPE_MIN_LENGTH = 5  # two chars before, and 2 chars after the slash ought to be reasonable


class BoefjeHandler(Handler):
    def __init__(self, job_runner: LocalBoefjeJobRunner, boefje_storage: BoefjeStorageInterface):
        self.job_runner = job_runner
        self.boefje_storage = boefje_storage

    def handle(self, task: Task) -> None:
        boefje_meta = task.data

        if not isinstance(boefje_meta, BoefjeMeta):
            raise ValueError("Plugin id does not belong to a boefje")

        logger.info("Starting boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))

        boefje_meta.started_at = datetime.now(timezone.utc)
        boefje_results: list[tuple[set, bytes | str]] = []

        try:
            boefje_results = self.job_runner.run(boefje_meta, boefje_meta.environment or {})
        except:
            logger.exception("Error running boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))
            boefje_results = [({"error/boefje"}, traceback.format_exc())]

            raise
        finally:
            boefje_meta.ended_at = datetime.now(timezone.utc)
            logger.info("Saving to Bytes for boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))

            self.boefje_storage.save_boefje_meta(boefje_meta)

            if boefje_results:
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
                    raw_file_id = self.boefje_storage.save_raw(
                        boefje_meta.id, output, _default_mime_types(boefje_meta.boefje).union(valid_mimetypes)
                    )
                    logger.info(
                        "Saved raw file %s for boefje %s[%s]", raw_file_id, boefje_meta.boefje.id, boefje_meta.id
                    )
            else:
                logger.info("No results for boefje %s[%s]", boefje_meta.boefje.id, boefje_meta.id)


def _default_mime_types(boefje: Boefje) -> set:
    mime_types = {f"boefje/{boefje.id}"}

    if boefje.version is not None:
        mime_types = mime_types.union({f"boefje/{boefje.id}-{boefje.version}"})

    return mime_types
