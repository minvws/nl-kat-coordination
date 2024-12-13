import traceback
from base64 import b64encode
from datetime import datetime, timezone

import structlog

from .interfaces import Handler, Task, BoefjeStorageInterface, File, StatusEnum, BoefjeOutput
from .job_models import BoefjeMeta
from .boefje_runner import LocalBoefjeJobRunner

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
        failed = False

        try:
            boefje_results = self.job_runner.run(boefje_meta, boefje_meta.environment or {})
        except:
            logger.exception("Error running boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))
            boefje_results = [({"error/boefje"}, traceback.format_exc())]
            failed = True

            raise
        finally:
            boefje_meta.ended_at = datetime.now(timezone.utc)
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

                files.append(File(
                    content=(b64encode(output) if isinstance(output, bytes) else b64encode(output.encode())).decode(),
                    tags=valid_mimetypes,
                ))

            boefje_output = BoefjeOutput(status=StatusEnum.FAILED if failed else StatusEnum.COMPLETED, files=files)
            raw_file_ids = self.boefje_storage.save_raws(boefje_meta.id, boefje_output)

            logger.info(
                "Saved %s raw files for boefje %s[%s]", len(raw_file_ids), boefje_meta.boefje.id, boefje_meta.id
            )
