from datetime import datetime, timezone
from logging import getLogger
from typing import List, Optional, Set, Type

from fastapi import APIRouter, Depends, Query, Path
from requests import RequestException

from octopoes.api.models import ServiceHealth, ValidatedObservation, ValidatedDeclaration
from octopoes.config.settings import Settings
from octopoes.core.app import bootstrap_octopoes
from octopoes.core.service import OctopoesService
from octopoes.models import OOI, Reference, ScanProfileBase, ScanProfile
from octopoes.models.datetime import TimezoneAwareDatetime
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.origin import Origin, OriginType
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import type_by_name
from octopoes.version import __version__
from octopoes.xtdb.client import XTDBHTTPClient

logger = getLogger(__name__)
router = APIRouter(prefix="/{client}")


# Dependencies
def extract_client(client: str = Path(...)) -> str:
    return client


def extract_valid_time(valid_time: Optional[TimezoneAwareDatetime] = Query(None)) -> datetime:
    if valid_time is None:
        return datetime.now(timezone.utc)
    return valid_time


def extract_required_valid_time(valid_time: TimezoneAwareDatetime) -> datetime:
    return valid_time


def extract_types(types: List[str] = Query(["OOI"])) -> Set[Type[OOI]]:
    try:
        return {type_by_name(t) for t in types}
    except KeyError as e:
        raise ObjectNotFoundException(str(e.args))


def extract_reference(reference: str = Query("")) -> Reference:
    return Reference.from_str(reference)


def settings() -> Settings:
    return Settings()


def xtdb_client(client: str = Depends(extract_client), settings_: Settings = Depends(settings)) -> XTDBHTTPClient:
    _, xtdb_http_client, _, rabbit_connection = bootstrap_octopoes(settings_, client)
    try:
        yield xtdb_http_client
    finally:
        rabbit_connection.close()


def octopoes_service(client: str = Depends(extract_client), settings_: Settings = Depends(settings)):
    octopoes, _, session, rabbit_connection = bootstrap_octopoes(settings_, client)

    try:
        yield octopoes
    finally:
        session.commit()
        rabbit_connection.close()


# Endpoints
@router.get("/health")
def health(
    xtdb: XTDBHTTPClient = Depends(xtdb_client),
) -> ServiceHealth:
    try:
        xtdb_status = xtdb.status()
        xtdb_health = ServiceHealth(
            service="xtdb",
            healthy=True,
            version=xtdb_status.version,
            additional=xtdb_status,
        )
    except RequestException as ex:
        xtdb_health = ServiceHealth(
            service="xtdb",
            healthy=False,
            additional="Cannot connect to XTDB at. Service possibly down",
        )
        logger.exception(ex)
    return ServiceHealth(
        service="octopoes",
        healthy=xtdb_health.healthy,
        version=__version__,
        results=[xtdb_health],
    )


# OOI-related endpoints
@router.get("/objects")
def list_objects(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    types: Set[Type[OOI]] = Depends(extract_types),
    offset: int = 0,
    limit: int = 20,
) -> List[OOI]:
    objects = octopoes.list_ooi(types, valid_time, offset, limit)
    return objects


@router.get("/object")
def get_object(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    reference: Reference = Depends(extract_reference),
) -> OOI:
    return octopoes.get_ooi(reference, valid_time)


@router.get("/objects/random")
def list_random_objects(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    amount: int = 1,
) -> List[OOI]:
    return octopoes.list_random_ooi(amount, valid_time)


@router.delete("/")
def delete_object(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    reference: Reference = Depends(extract_reference),
) -> None:
    octopoes.ooi_repository.delete(reference, valid_time)


@router.get("/tree")
def get_tree(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    types: Set[Type[OOI]] = Depends(extract_types),
    reference: Reference = Depends(extract_reference),
    depth: int = 1,
) -> ReferenceTree:
    return octopoes.get_ooi_tree(
        reference,
        valid_time,
        types,
        depth,
    )


# Origin-related endpoints
@router.get("/origins")
def list_origins(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    reference: Reference = Depends(extract_reference),
) -> List[Origin]:
    return octopoes.origin_repository.list_by_result(reference, valid_time)


@router.post("/observations")
def save_observation(
    observation: ValidatedObservation,
    octopoes: OctopoesService = Depends(octopoes_service),
) -> None:
    origin = Origin(
        origin_type=OriginType.OBSERVATION,
        method=observation.method,
        source=observation.source,
        result=[ooi.reference for ooi in observation.result],
        task_id=observation.task_id,
    )
    octopoes.save_origin(origin, observation.result, observation.valid_time)


@router.post("/declarations")
def save_declaration(
    declaration: ValidatedDeclaration,
    octopoes: OctopoesService = Depends(octopoes_service),
):
    origin = Origin(
        origin_type=OriginType.DECLARATION,
        method="manual",
        source=declaration.ooi.reference,
        result=[declaration.ooi.reference],
    )
    octopoes.save_origin(origin, [declaration.ooi], declaration.valid_time)


# ScanProfile-related endpoints
@router.get("/scan_profiles")
def scan_profiles(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    scan_profile_type: Optional[str] = Query(None),
) -> List[ScanProfileBase]:
    return octopoes.scan_profile_repository.list(scan_profile_type, valid_time)


@router.put("/scan_profiles")
def save_scan_profile(
    scan_profile: ScanProfile,
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_required_valid_time),
):
    octopoes.scan_profile_repository.save(scan_profile, valid_time)


@router.get("/scan_profiles/recalculate")
def recalculate_scan_profile(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    reference: Reference = Depends(extract_reference),
):
    ooi = octopoes.get_ooi(reference, valid_time)
    octopoes._calculate_scan_profile(ooi, ooi.scan_profile, valid_time)
