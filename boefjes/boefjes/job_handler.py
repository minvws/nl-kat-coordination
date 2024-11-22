import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from typing import cast

import structlog

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.clients.scheduler_client import get_octopoes_api_connector
from boefjes.config import settings
from boefjes.dependencies.plugins import PluginService
from boefjes.docker_boefjes_runner import DockerBoefjesRunner
from boefjes.interfaces import BoefjeJobRunner, Handler, Task
from boefjes.job_models import BoefjeMeta
from boefjes.normalizer_interfaces import NormalizerJobRunner
from boefjes.plugins.models import _default_mime_types
from octopoes.api.models import Affirmation, Declaration, Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference, ScanLevel

MIMETYPE_MIN_LENGTH = 5  # two chars before, and 2 chars after the slash ought to be reasonable

logger = structlog.get_logger(__name__)

bytes_api_client = BytesAPIClient(
    str(settings.bytes_api), username=settings.bytes_username, password=settings.bytes_password
)


class BoefjeHandler(Handler):
    def __init__(
        self,
        job_runner: BoefjeJobRunner,
        plugin_service: PluginService,
        docker_runner: DockerBoefjesRunner,
        bytes_client: BytesAPIClient,
    ):
        self.job_runner = job_runner
        self.plugin_service = plugin_service
        self.docker_runner = docker_runner
        self.bytes_client = bytes_client

    def handle(self, task: Task) -> None:
        boefje_meta = task.data
        plugin = self.plugin_service.by_plugin_id(boefje_meta.boefje.id, boefje_meta.organization)

        if not isinstance(boefje_meta, BoefjeMeta):
            raise ValueError("Plugin id does not belong to a boefje")

        logger.info("Handling boefje %s[task_id=%s]", boefje_meta.boefje.id, str(boefje_meta.id))

        # Check if this boefje is container-native, if so, continue using the Docker boefjes runner
        if boefje_meta.arguments["oci_image"]:
            logger.info(
                "Delegating boefje %s[task_id=%s] to Docker runner with OCI image [%s]",
                boefje_meta.boefje.id,
                str(boefje_meta.id),
                boefje_meta.arguments["oci_image"],
            )
            return self.docker_runner.run(task)

        boefje_meta.runnable_hash = plugin.runnable_hash

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

            self.bytes_client.save_boefje_meta(boefje_meta)

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
                    raw_file_id = self.bytes_client.save_raw(
                        boefje_meta.id, output, _default_mime_types(boefje_meta.boefje).union(valid_mimetypes)
                    )
                    logger.info(
                        "Saved raw file %s for boefje %s[%s]", raw_file_id, boefje_meta.boefje.id, boefje_meta.id
                    )
            else:
                logger.info("No results for boefje %s[%s]", boefje_meta.boefje.id, boefje_meta.id)


class NormalizerHandler(Handler):
    def __init__(
        self,
        job_runner: NormalizerJobRunner,
        bytes_client: BytesAPIClient,
        whitelist: dict[str, int] | None = None,
        octopoes_factory: Callable[[str], OctopoesAPIConnector] = get_octopoes_api_connector,
    ):
        self.job_runner = job_runner
        self.bytes_client: BytesAPIClient = bytes_client
        self.whitelist = whitelist or {}
        self.octopoes_factory = octopoes_factory

    def handle(self, task: Task) -> None:
        normalizer_meta = task.data
        logger.info("Handling normalizer %s[%s]", normalizer_meta.normalizer.id, normalizer_meta.id)

        raw = self.bytes_client.get_raw(normalizer_meta.raw_data.id)

        normalizer_meta.started_at = datetime.now(timezone.utc)

        try:
            results = self.job_runner.run(normalizer_meta, raw)
            connector = self.octopoes_factory(normalizer_meta.raw_data.boefje_meta.organization)

            logger.info("Obtained results %s", str(results))

            for observation in results.observations:
                for ooi in observation.results:
                    if ooi.primary_key == observation.input_ooi:
                        logger.warning(
                            'Normalizer "%s" returned input [%s]', normalizer_meta.normalizer.id, observation.input_ooi
                        )
                reference = Reference.from_str(observation.input_ooi)
                connector.save_observation(
                    Observation(
                        method=normalizer_meta.normalizer.id,
                        source=reference,
                        source_method=normalizer_meta.raw_data.boefje_meta.boefje.id,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                        result=[ooi for ooi in observation.results if ooi.primary_key != observation.input_ooi],
                    )
                )

            for declaration in results.declarations:
                connector.save_declaration(
                    Declaration(
                        method=normalizer_meta.normalizer.id,
                        source_method=normalizer_meta.raw_data.boefje_meta.boefje.id,
                        ooi=declaration.ooi,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                    )
                )

            for affirmation in results.affirmations:
                connector.save_affirmation(
                    Affirmation(
                        method=normalizer_meta.normalizer.id,
                        source_method=normalizer_meta.raw_data.boefje_meta.boefje.id,
                        ooi=affirmation.ooi,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                    )
                )

            if (
                normalizer_meta.raw_data.boefje_meta.input_ooi  # No input OOI means no deletion propagation
                and not (results.observations or results.declarations or results.affirmations)
            ):
                # There were no results found, which we still need to signal to Octopoes for deletion propagation

                connector.save_observation(
                    Observation(
                        method=normalizer_meta.normalizer.id,
                        source=Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi),
                        source_method=normalizer_meta.raw_data.boefje_meta.boefje.id,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                        result=[],
                    )
                )

            corrected_scan_profiles = []
            for profile in results.scan_profiles:
                profile.level = ScanLevel(
                    min(profile.level, self.whitelist.get(normalizer_meta.normalizer.id, profile.level))
                )
                corrected_scan_profiles.append(profile)

            validated_scan_profiles = [
                profile
                for profile in corrected_scan_profiles
                if self.whitelist and profile.level <= self.whitelist.get(normalizer_meta.normalizer.id, -1)
            ]
            if validated_scan_profiles:
                connector.save_many_scan_profiles(
                    results.scan_profiles,
                    # Mypy doesn't seem to be able to figure out that ended_at is a datetime
                    valid_time=cast(datetime, normalizer_meta.raw_data.boefje_meta.ended_at),
                )
        finally:
            normalizer_meta.ended_at = datetime.now(timezone.utc)
            self.bytes_client.save_normalizer_meta(normalizer_meta)

        logger.info("Done with normalizer %s[%s]", normalizer_meta.normalizer.id, normalizer_meta.id)


class InvalidWhitelist(Exception):
    pass
