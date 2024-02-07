import logging
import os
import traceback
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import requests
from pydantic.tools import parse_obj_as
from requests import RequestException

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.config import settings
from boefjes.docker_boefjes_runner import DockerBoefjesRunner
from boefjes.job_models import (
    BoefjeMeta,
    NormalizerMeta,
    NormalizerPlainOOI,
    NormalizerScanProfile,
)
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.plugins.models import _default_mime_types
from boefjes.runtime_interfaces import BoefjeJobRunner, Handler, NormalizerJobRunner
from octopoes.api.models import Declaration, Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, Reference, ScanProfile
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.types import OOIType

logger = logging.getLogger(__name__)

bytes_api_client = BytesAPIClient(
    str(settings.bytes_api),
    username=settings.bytes_username,
    password=settings.bytes_password,
)


def _find_ooi_in_past(reference: Reference, connector: OctopoesAPIConnector, lookback_days: int = 4) -> OOI:
    # Source OOIs may not live in XTDB since we currently have TTLs in place (to be removed soon).
    valid_time = datetime.now(timezone.utc)

    for days_in_past in range(lookback_days):
        try:
            return connector.get(reference, valid_time=valid_time)
        except ObjectNotFoundException:
            logger.debug(
                "Object %s not found in Octopoes, looking into other valid times...",
                reference,
            )
            date = datetime.now(timezone.utc) - timedelta(days=days_in_past)
            valid_time = date.replace(hour=0, minute=0, second=0, microsecond=0)

    raise ObjectNotFoundException(f"Object {reference} not found in Octopoes")


def _serialize_value(value: Any, required: bool) -> Any:
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
    if isinstance(value, (int, float)):
        return value
    else:
        return str(value)


def serialize_ooi(ooi: OOI):
    serialized_oois = {}
    for key, value in ooi:
        if key not in ooi.model_fields:
            continue
        serialized_oois[key] = _serialize_value(value, ooi.model_fields[key].is_required())
    return serialized_oois


def get_octopoes_api_connector(org_code: str) -> OctopoesAPIConnector:
    return OctopoesAPIConnector(str(settings.octopoes_api), org_code)


def get_environment_settings(boefje_meta: BoefjeMeta, environment_keys: List[str]) -> Dict[str, str]:
    try:
        katalogus_api = str(settings.katalogus_api).rstrip("/")
        response = requests.get(
            f"{katalogus_api}/v1/organisations/{boefje_meta.organization}/{boefje_meta.boefje.id}/settings"
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
    except RequestException:
        logger.exception("Error getting environment settings")
        raise


class BoefjeHandler(Handler):
    def __init__(
        self,
        job_runner: BoefjeJobRunner,
        local_repository: LocalPluginRepository,
        bytes_client: BytesAPIClient,
        octopoes_factory=get_octopoes_api_connector,
    ):
        self.job_runner = job_runner
        self.local_repository = local_repository
        self.bytes_client = bytes_client
        self.octopoes_factory = octopoes_factory

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
            boefje_meta.arguments["input"] = serialize_ooi(
                _find_ooi_in_past(
                    Reference.from_str(boefje_meta.input_ooi),
                    self.octopoes_factory(boefje_meta.organization),
                )
            )

        env_keys = boefje_resource.environment_keys

        boefje_meta.runnable_hash = boefje_resource.runnable_hash
        boefje_meta.environment = get_environment_settings(boefje_meta, env_keys) if env_keys else {}

        mime_types = _default_mime_types(boefje_meta.boefje)

        logger.info("Starting boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))

        boefje_meta.started_at = datetime.now(timezone.utc)

        boefje_results = None

        try:
            boefje_results = self.job_runner.run(boefje_meta, boefje_meta.environment)
        except Exception:
            logger.exception("Error running boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))
            boefje_results = [({"error/boefje"}, traceback.format_exc())]

            raise
        finally:
            boefje_meta.ended_at = datetime.now(timezone.utc)
            logger.info("Saving to Bytes for boefje %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))

            self.bytes_client.save_boefje_meta(boefje_meta)

            if boefje_results:
                for boefje_added_mime_types, output in boefje_results:
                    raw_file_id = self.bytes_client.save_raw(
                        boefje_meta.id, output, mime_types.union(boefje_added_mime_types)
                    )
                    logger.debug(
                        "Saved raw file %s for boefje %s[%s]", raw_file_id, boefje_meta.boefje.id, boefje_meta.id
                    )

            logger.info("Done with boefje for %s[%s]", boefje_meta.boefje.id, str(boefje_meta.id))


class NormalizerHandler(Handler):
    def __init__(
        self,
        job_runner: NormalizerJobRunner,
        bytes_client: BytesAPIClient,
        whitelist: Optional[Dict[str, int]] = None,
        octopoes_factory: Callable[[str], OctopoesAPIConnector] = 3,
    ):
        self.job_runner = job_runner
        self.bytes_client: BytesAPIClient = bytes_client
        self.whitelist = whitelist
        self.octopoes_factory = octopoes_factory

    def handle(self, normalizer_meta: NormalizerMeta) -> None:
        logger.info("Handling normalizer %s[%s]", normalizer_meta.normalizer.id, normalizer_meta.id)

        raw = self.bytes_client.get_raw(normalizer_meta.raw_data.id)

        normalizer_meta.started_at = datetime.now(timezone.utc)

        try:
            results = self.job_runner.run(normalizer_meta, raw)
            connector = self.octopoes_factory(normalizer_meta.raw_data.boefje_meta.organization)

            for observation in results.observations:
                reference = Reference.from_str(observation.input_ooi)
                connector.save_observation(
                    Observation(
                        method=normalizer_meta.normalizer.id,
                        source=reference,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                        result=[self._parse_ooi(result) for result in observation.results],
                    )
                )

            for declaration in results.declarations:
                connector.save_declaration(
                    Declaration(
                        method=normalizer_meta.normalizer.id,
                        ooi=self._parse_ooi(declaration.ooi),
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                    )
                )

            corrected_scan_profiles = []
            for profile in results.scan_profiles:
                profile.level = min(profile.level, self.whitelist.get(normalizer_meta.normalizer.id, profile.level))
                corrected_scan_profiles.append(profile)

            validated_scan_profiles = [
                profile
                for profile in corrected_scan_profiles
                if self.whitelist and profile.level <= self.whitelist.get(normalizer_meta.normalizer.id, -1)
            ]
            if validated_scan_profiles:
                connector.save_many_scan_profiles(
                    [self._parse_scan_profile(scan_profile) for scan_profile in results.scan_profiles],
                    valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                )
        finally:
            normalizer_meta.ended_at = datetime.now(timezone.utc)
            self.bytes_client.save_normalizer_meta(normalizer_meta)

        logger.info("Done with normalizer %s[%s]", normalizer_meta.normalizer.id, normalizer_meta.id)

    @staticmethod
    def _parse_ooi(result: NormalizerPlainOOI):
        return parse_obj_as(OOIType, result.model_dump())

    @staticmethod
    def _parse_scan_profile(result: NormalizerScanProfile):
        return parse_obj_as(ScanProfile, result.model_dump())


class InvalidWhitelist(Exception):
    pass
