import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

from octopoes.api.models import Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException

from boefjes.models import Normalizer
from bytes_client import BytesAPIClient
from config import settings
from job import BoefjeMeta, NormalizerMeta
from runner import NormalizerJobRunner, BoefjeJobRunner

logger = logging.getLogger(__name__)
bytes_api_client = BytesAPIClient(
    settings.bytes_api,
    username=settings.bytes_username,
    password=settings.bytes_password,
)


def _find_ooi_in_past(
    reference: Reference, connector: OctopoesAPIConnector, lookback_days: int = 4
) -> OOI:
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


def handle_boefje_job(
    boefje_meta: BoefjeMeta, job_runner: BoefjeJobRunner
) -> BoefjeMeta:
    try:
        logger.info("Starting boefje %s[%s]", boefje_meta.boefje.id, boefje_meta.id)

        try:
            _, job_output = job_runner.run()
            raw_output = job_output.data
            mime_types = job_output.mime_types
        except Exception as exc:
            logger.info(
                "Error while running boefje %s[%s]",
                boefje_meta.boefje.id,
                boefje_meta.id,
            )
            raw_output = str(exc)
            mime_types = {"error/boefje"}
            boefje_meta.ended_at = datetime.now(timezone.utc)

        bytes_api_client.save_boefje_meta(boefje_meta)
        bytes_api_client.save_raw(boefje_meta.id, raw_output, mime_types)

        logger.info(
            "Done with boefje for %s[%s]",
            boefje_meta.boefje.id,
            boefje_meta.id,
        )

        return boefje_meta

    except Exception as exc:
        logger.exception("Error while handling a boefje job")
        raise exc


def handle_normalizer_job(
    normalizer_meta: NormalizerMeta, normalizer: Normalizer, package: str
) -> None:
    try:
        logger.info(
            "Starting normalizer %s[%s]",
            normalizer_meta.normalizer.name,
            normalizer_meta.id,
        )

        bytes_api_client.login()
        raw = bytes_api_client.get_raw(normalizer_meta.boefje_meta.id)

        job_runner = NormalizerJobRunner(normalizer_meta, normalizer, package, raw)
        job_runner.run()

        reference = Reference.from_str(normalizer_meta.boefje_meta.input_ooi)

        observation = Observation(
            method=normalizer_meta.normalizer.name,
            source=reference,
            task_id=normalizer_meta.id,
            valid_time=normalizer_meta.boefje_meta.ended_at,
            result=job_runner.results,
        )

        get_octopoes_api_connector(
            normalizer_meta.boefje_meta.organization
        ).save_observation(observation)
        bytes_api_client.save_normalizer_meta(normalizer_meta)

        logger.info(
            "Done with normalizer %s[%s]",
            normalizer_meta.normalizer.name,
            normalizer_meta.id,
        )

    except Exception as exc:
        logger.error("Error while handling a normalizer job")
        raise exc


def get_octopoes_api_connector(org_code: str):
    return OctopoesAPIConnector(settings.octopoes_api, org_code)
