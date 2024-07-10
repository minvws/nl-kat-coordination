import os
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any, cast

import httpx
import structlog
from httpx import HTTPError

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.config import settings
from boefjes.docker_boefjes_runner import DockerBoefjesRunner
from boefjes.job_models import BoefjeMeta, NormalizerMeta, SerializedOOI, SerializedOOIValue
from boefjes.local_repository import LocalPluginRepository
from boefjes.plugins.models import _default_mime_types
from boefjes.runtime_interfaces import BoefjeJobRunner, Handler, NormalizerJobRunner
from octopoes.api.models import Affirmation, Declaration, Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, Reference, ScanLevel
from octopoes.models.exception import ObjectNotFoundException

MIMETYPE_MIN_LENGTH = 5  # two chars before, and 2 chars after the slash ought to be reasonable

logger = structlog.get_logger(__name__)

bytes_api_client = BytesAPIClient(
    str(settings.bytes_api),
    username=settings.bytes_username,
    password=settings.bytes_password,
)


def _serialize_value(value: Any, required: bool) -> SerializedOOIValue:
    if isinstance(value, list):
        return [_serialize_value(item, required) for item in value]
    if isinstance(value, Reference):
        try:
            return value.tokenized.root
        except AttributeError:
            if required:
                raise

            return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, int | float):
        return value
    else:
        return str(value)


def serialize_ooi(ooi: OOI) -> SerializedOOI:
    serialized_oois = {}
    for key, value in ooi:
        if key not in ooi.model_fields:
            continue
        serialized_oois[key] = _serialize_value(value, ooi.model_fields[key].is_required())
    return serialized_oois


def get_octopoes_api_connector(org_code: str) -> OctopoesAPIConnector:
    return OctopoesAPIConnector(str(settings.octopoes_api), org_code)


def get_environment_settings(boefje_meta: BoefjeMeta, environment_keys: list[str]) -> dict[str, str]:
    try:
        katalogus_api = str(settings.katalogus_api).rstrip("/")
        response = httpx.get(
            f"{katalogus_api}/v1/organisations/{boefje_meta.organization}/{boefje_meta.boefje.id}/settings",
            timeout=30,
        )
        response.raise_for_status()
        environment = response.json()

        # Add prefixed BOEFJE_* global environment variables
        for key, value in os.environ.items():
            if key.startswith("BOEFJE_"):
                katalogus_key = key.split("BOEFJE_", 1)[1]
                # Only pass the environment variable if it is not explicitly set through the katalogus,
                # if and only if they are defined in boefje.json
                if katalogus_key in environment_keys and katalogus_key not in environment:
                    environment[katalogus_key] = value

        return {k: str(v) for k, v in environment.items() if k in environment_keys}
    except HTTPError:
        logger.exception("Error getting environment settings")
        raise


class BoefjeHandler(Handler):
    def __init__(
        self,
        job_runner: BoefjeJobRunner,
        local_repository: LocalPluginRepository,
        bytes_client: BytesAPIClient,
    ):
        self.job_runner = job_runner
        self.local_repository = local_repository
        self.bytes_client = bytes_client

    def handle(self, boefje_meta: BoefjeMeta) -> None:
        logger.info("Handling boefje %s[task_id=%s]", boefje_meta.boefje.id, str(boefje_meta.id))

        # Check if this boefje is container-native, if so, continue using the Docker boefjes runner
        boefje_resource = self.local_repository.by_id(boefje_meta.boefje.id)
        if boefje_resource.oci_image:
            logger.info(
                "Delegating boefje %s[task_id=%s] to Docker runner with OCI image [%s]",
                boefje_meta.boefje.id,
                str(boefje_meta.id),
                boefje_resource.oci_image,
            )
            docker_runner = DockerBoefjesRunner(boefje_resource, boefje_meta)
            return docker_runner.run()

        if boefje_meta.input_ooi:
            reference = Reference.from_str(boefje_meta.input_ooi)
            try:
                ooi = get_octopoes_api_connector(boefje_meta.organization).get(
                    reference, valid_time=datetime.now(timezone.utc)
                )
            except ObjectNotFoundException as e:
                raise ObjectNotFoundException(f"Object {reference} not found in Octopoes") from e

            boefje_meta.arguments["input"] = serialize_ooi(ooi)

        env_keys = boefje_resource.environment_keys

        boefje_meta.runnable_hash = boefje_resource.runnable_hash
        boefje_meta.environment = get_environment_settings(boefje_meta, env_keys) if env_keys else {}

        mime_types = _default_mime_types(boefje_meta.boefje)

        logger.info("Starting boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))

        boefje_meta.started_at = datetime.now(timezone.utc)

        boefje_results: list[tuple[set, bytes | str]]

        try:
            boefje_results = self.job_runner.run(boefje_meta, boefje_meta.environment)
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
                    raw_file_id = self.bytes_client.save_raw(boefje_meta.id, output, mime_types.union(valid_mimetypes))
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

    def handle(self, normalizer_meta: NormalizerMeta) -> None:
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
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                        result=[ooi for ooi in observation.results if ooi.primary_key != observation.input_ooi],
                    )
                )

            for declaration in results.declarations:
                connector.save_declaration(
                    Declaration(
                        method=normalizer_meta.normalizer.id,
                        ooi=declaration.ooi,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                    )
                )

            for affirmation in results.affirmations:
                connector.save_affirmation(
                    Affirmation(
                        method=normalizer_meta.normalizer.id,
                        ooi=affirmation.ooi,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
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
