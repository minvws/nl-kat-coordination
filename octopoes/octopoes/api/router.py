import uuid
from datetime import datetime, timezone
from logging import getLogger
from typing import Dict, List, Optional, Set, Type

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from requests import RequestException

from octopoes.api.models import ServiceHealth, ValidatedDeclaration, ValidatedObservation
from octopoes.config.settings import Settings
from octopoes.core.app import bootstrap_octopoes, get_xtdb_client
from octopoes.core.service import OctopoesService
from octopoes.models import (
    DEFAULT_SCAN_LEVEL_FILTER,
    DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    OOI,
    Reference,
    ScanLevel,
    ScanProfile,
    ScanProfileBase,
    ScanProfileType,
)
from octopoes.models.datetime import TimezoneAwareDatetime
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.explanation import InheritanceSection
from octopoes.models.origin import Origin, OriginParameter, OriginType
from octopoes.models.pagination import Paginated
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import type_by_name
from octopoes.version import __version__
from octopoes.xtdb.client import XTDBSession
from octopoes.xtdb.exceptions import NoMultinode, XTDBException

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


def xtdb_session(client: str = Depends(extract_client), settings_: Settings = Depends(settings)) -> XTDBSession:
    xtdb_client_ = get_xtdb_client(settings_.xtdb_uri, client, settings_.xtdb_type)
    return XTDBSession(xtdb_client_)


def octopoes_service(
    client: str = Depends(extract_client),
    xtdb_session_: XTDBSession = Depends(xtdb_session),
    settings_: Settings = Depends(settings),
):
    octopoes, _, session, rabbit_connection = bootstrap_octopoes(settings_, client, xtdb_session_)
    try:
        yield octopoes
    finally:
        rabbit_connection.close()


# Endpoints
@router.get("/health")
def health(
    xtdb_session_: XTDBSession = Depends(xtdb_session),
) -> ServiceHealth:
    try:
        xtdb_status = xtdb_session_.client.status()
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
    scan_level: Set[ScanLevel] = Query(DEFAULT_SCAN_LEVEL_FILTER),
    scan_profile_type: Set[ScanProfileType] = Query(DEFAULT_SCAN_PROFILE_TYPE_FILTER),
    offset: int = 0,
    limit: int = 20,
) -> Paginated[OOI]:
    objects = octopoes.list_ooi(types, valid_time, offset, limit, scan_level, scan_profile_type)
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
    scan_level: Set[ScanLevel] = Query(DEFAULT_SCAN_LEVEL_FILTER),
) -> List[OOI]:
    return octopoes.list_random_ooi(valid_time, amount, scan_level)


@router.delete("/")
def delete_object(
    xtdb_session_: XTDBSession = Depends(xtdb_session),
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    reference: Reference = Depends(extract_reference),
) -> None:
    octopoes.ooi_repository.delete(reference, valid_time)
    xtdb_session_.commit()


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


@router.get("/origin_parameters")
def list_origin_parameters(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    origin_id: Set[str] = Query(default=set()),
) -> List[OriginParameter]:
    return octopoes.origin_parameter_repository.list_by_origin(origin_id, valid_time)


@router.post("/observations")
def save_observation(
    observation: ValidatedObservation,
    xtdb_session_: XTDBSession = Depends(xtdb_session),
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
    xtdb_session_.commit()


@router.post("/declarations")
def save_declaration(
    declaration: ValidatedDeclaration,
    xtdb_session_: XTDBSession = Depends(xtdb_session),
    octopoes: OctopoesService = Depends(octopoes_service),
) -> None:
    origin = Origin(
        origin_type=OriginType.DECLARATION,
        method=declaration.method if declaration.method else "manual",
        source=declaration.ooi.reference,
        result=[declaration.ooi.reference],
        task_id=declaration.task_id if declaration.task_id else str(uuid.uuid4()),
    )
    octopoes.save_origin(origin, [declaration.ooi], declaration.valid_time)
    xtdb_session_.commit()


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
    xtdb_session_: XTDBSession = Depends(xtdb_session),
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_required_valid_time),
) -> None:
    try:
        old_scan_profile = octopoes.scan_profile_repository.get(scan_profile.reference, valid_time)
    except ObjectNotFoundException:
        old_scan_profile = None

    octopoes.scan_profile_repository.save(old_scan_profile, scan_profile, valid_time)
    xtdb_session_.commit()


@router.get("/scan_profiles/recalculate")
def recalculate_scan_profiles(
    xtdb_session_: XTDBSession = Depends(xtdb_session),
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_required_valid_time),
) -> None:
    octopoes.recalculate_scan_profiles(valid_time)
    xtdb_session_.commit()


@router.get("/scan_profiles/inheritance")
def get_scan_profile_inheritance(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    reference: Reference = Depends(extract_reference),
) -> List[InheritanceSection]:
    ooi = octopoes.get_ooi(reference, valid_time)
    start = InheritanceSection(
        reference=ooi.reference, level=ooi.scan_profile.level, scan_profile_type=ooi.scan_profile.scan_profile_type
    )
    if ooi.scan_profile.scan_profile_type == ScanProfileType.DECLARED:
        return [start]
    return octopoes.get_scan_profile_inheritance(reference, valid_time, [start])


@router.get("/finding_types/count")
def get_finding_type_count(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
) -> Dict[str, int]:
    return octopoes.ooi_repository.get_finding_type_count(valid_time)


@router.post("/node")
def create_node(xtdb_session_: XTDBSession = Depends(xtdb_session)) -> None:
    try:
        xtdb_session_.client.create_node()
    except NoMultinode:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="XTDB multinode is not set up for Octopoes."
        )
    except XTDBException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Creating node failed") from e


@router.delete("/node")
def delete_node(xtdb_session_: XTDBSession = Depends(xtdb_session)) -> None:
    try:
        xtdb_session_.client.delete_node()
    except NoMultinode:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="XTDB multinode is not set up for Octopoes."
        )
    except XTDBException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Deleting node failed") from e


@router.post("/bits/recalculate")
def recalculate_bits(
    xtdb_session_: XTDBSession = Depends(xtdb_session), octopoes: OctopoesService = Depends(octopoes_service)
) -> int:
    inference_count = octopoes.recalculate_bits()
    xtdb_session_.commit()
    return inference_count
