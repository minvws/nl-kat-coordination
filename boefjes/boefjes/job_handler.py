import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, List, Dict, Set

import requests

from octopoes.models.types import OOIType
from pydantic.tools import parse_obj_as

from boefjes.katalogus.local_repository import LocalPluginRepository
from octopoes.api.models import Observation, Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from requests import RequestException

from boefjes.runtime_interfaces import Handler, BoefjeJobRunner, NormalizerJobRunner

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.config import settings
from boefjes.job_models import (
    BoefjeMeta,
    NormalizerMeta,
    NormalizerPlainOOI,
)

logger = logging.getLogger(__name__)
bytes_api_client = BytesAPIClient(
    settings.bytes_api,
    username=settings.bytes_username,
    password=settings.bytes_password,
)


def _find_ooi_in_past(reference: Reference, connector: OctopoesAPIConnector, lookback_days: int = 4) -> OOI:
    # Source OOIs may not live in crux since we currently have TTLs in place (to be removed soon).
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
            return value.tokenized.dict()["__root__"]
        except IndexError as error:
            if required:
                raise error

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
        if key not in ooi.__fields__:
            continue
        serialized_oois[key] = _serialize_value(value, ooi.__fields__[key].required)
    return serialized_oois


def get_environment_settings(boefje_meta: BoefjeMeta, environment_keys: List[str]) -> Dict[str, str]:
    try:
        environment = requests.get(
            f"{settings.katalogus_api}/v1/organisations/{boefje_meta.organization}/{boefje_meta.boefje.id}/settings"
        ).json()

        return {k: v for k, v in environment.items() if k in environment_keys}
    except RequestException:
        logger.exception("Error getting environment settings")

    return {}


def _collect_default_mime_types(boefje_meta: BoefjeMeta) -> Set[str]:
    boefje_id = boefje_meta.boefje.id

    mime_types = {
        boefje_id,
        f"boefje/{boefje_id}",
        f"boefje/{boefje_id}-{boefje_meta.parameterized_arguments_hash}",
    }

    if boefje_meta.boefje.version is not None:
        mime_types = mime_types.union(
            {
                f"boefje/{boefje_id}-{boefje_meta.boefje.version}",
                f"boefje/{boefje_id}-{boefje_meta.parameterized_arguments_hash}-{boefje_meta.boefje.version}",
            }
        )

    return mime_types


class BoefjeHandler(Handler):
    def __init__(self, job_runner, local_repository: LocalPluginRepository):
        self.job_runner: BoefjeJobRunner = job_runner
        self.local_repository: LocalPluginRepository = local_repository  # TODO: abstract (e.g. LXD version)

    def handle(self, boefje_meta: BoefjeMeta) -> None:
        logger.info("Handling boefje %s[%s]", boefje_meta.boefje.id, boefje_meta.id)

        if boefje_meta.input_ooi:
            boefje_meta.arguments["input"] = serialize_ooi(
                _find_ooi_in_past(
                    Reference.from_str(boefje_meta.input_ooi),
                    get_octopoes_api_connector(boefje_meta.organization),
                )
            )

        env_keys = self.local_repository.by_id(boefje_meta.boefje.id).environment_keys
        environment = get_environment_settings(boefje_meta, env_keys)

        mime_types = _collect_default_mime_types(boefje_meta)
        logger.info("Starting boefje %s[%s]", boefje_meta.boefje.id, boefje_meta.id)

        boefje_meta.started_at = datetime.now(timezone.utc)
        boefje_results = None

        try:
            boefje_results = self.job_runner.run(boefje_meta, environment)
        except Exception as e:
            logger.exception("Error running boefje %s[%s]", boefje_meta.boefje.id, boefje_meta.id)
            boefje_results = [({"error/boefje"}, str(e))]

            raise
        finally:
            boefje_meta.ended_at = datetime.now(timezone.utc)
            logger.info("Saving to Bytes for boefje boefje %s[%s]", boefje_meta.boefje.id, boefje_meta.id)

            bytes_api_client.login()
            bytes_api_client.save_boefje_meta(boefje_meta)

            if boefje_results:
                for boefje_added_mime_types, output in boefje_results:
                    bytes_api_client.save_raw(boefje_meta.id, output, mime_types.union(boefje_added_mime_types))

            logger.info("Done with boefje for %s[%s]", boefje_meta.boefje.id, boefje_meta.id)


class NormalizerHandler(Handler):
    def __init__(self, job_runner):
        self.job_runner: NormalizerJobRunner = job_runner

    def handle(self, normalizer_meta: NormalizerMeta) -> None:
        logger.info("Handling normalizer %s[%s]", normalizer_meta.normalizer.id, normalizer_meta.id)

        bytes_api_client.login()
        raw = bytes_api_client.get_raw(normalizer_meta.raw_data.boefje_meta.id, normalizer_meta.raw_data.id)

        normalizer_meta.started_at = datetime.now(timezone.utc)

        try:
            results = self.job_runner.run(normalizer_meta, raw)
            connector = get_octopoes_api_connector(normalizer_meta.raw_data.boefje_meta.organization)

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
        finally:
            normalizer_meta.ended_at = datetime.now(timezone.utc)
            bytes_api_client.save_normalizer_meta(normalizer_meta)

        logger.info("Done with normalizer %s[%s]", normalizer_meta.normalizer.id, normalizer_meta.id)

    @staticmethod
    def _parse_ooi(result: NormalizerPlainOOI):
        return parse_obj_as(OOIType, result.dict())


def get_octopoes_api_connector(org_code: str):
    return OctopoesAPIConnector(settings.octopoes_api, org_code)
