import uuid
from collections import Counter
from datetime import datetime, timezone
from logging import getLogger
from typing import Generator, List, Optional, Set, Type

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from requests import RequestException

from octopoes.api.models import ServiceHealth, ValidatedDeclaration, ValidatedObservation
from octopoes.config.settings import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    DEFAULT_SCAN_LEVEL_FILTER,
    DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    DEFAULT_SEVERITY_FILTER,
    Settings,
)
from octopoes.core.app import bootstrap_octopoes, get_xtdb_client
from octopoes.core.service import OctopoesService
from octopoes.models import (
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
from octopoes.models.ooi.findings import Finding, RiskLevelSeverity
from octopoes.models.origin import Origin, OriginParameter, OriginType
from octopoes.models.pagination import Paginated
from octopoes.models.path import Path as ObjectPath
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import type_by_name
from octopoes.version import __version__
from octopoes.xtdb.client import XTDBSession
from octopoes.xtdb.exceptions import NoMultinode, XTDBException
from octopoes.xtdb.query import Query as XTDBQuery

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


def extract_references(references: List[str]) -> List[Reference]:
    return [Reference.from_str(reference) for reference in references]


def settings() -> Settings:
    return Settings()


def xtdb_session(
    client: str = Depends(extract_client), settings_: Settings = Depends(settings)
) -> Generator[XTDBSession, None, None]:
    yield XTDBSession(get_xtdb_client(settings_.xtdb_uri, client, settings_.xtdb_type))


def octopoes_service(
    client: str = Depends(extract_client),
    session: XTDBSession = Depends(xtdb_session),
    settings_: Settings = Depends(settings),
) -> OctopoesService:
    return bootstrap_octopoes(settings_, client, session)


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
@router.get("/objects", tags=["Objects"])
def list_objects(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    types: Set[Type[OOI]] = Depends(extract_types),
    scan_level: Set[ScanLevel] = Query(DEFAULT_SCAN_LEVEL_FILTER),
    scan_profile_type: Set[ScanProfileType] = Query(DEFAULT_SCAN_PROFILE_TYPE_FILTER),
    offset: int = 0,
    limit: int = 20,
):
    return octopoes.list_ooi(types, valid_time, offset, limit, scan_level, scan_profile_type)


@router.get("/query", tags=["Objects"])
def query(
    path: str,
    source: Optional[Reference] = None,
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    offset: int = DEFAULT_OFFSET,
    limit: int = DEFAULT_LIMIT,
):
    object_path = ObjectPath.parse(path)
    xtdb_query = XTDBQuery.from_path(object_path).offset(offset).limit(limit)

    if source is not None and object_path.segments:
        xtdb_query = xtdb_query.where(object_path.segments[0].source_type, primary_key=str(source))

    return octopoes.ooi_repository.query(xtdb_query, valid_time)


@router.post("/objects/load_bulk", tags=["Objects"])
def load_objects_bulk(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    references: Set[Reference] = Depends(extract_references),
):
    return octopoes.ooi_repository.load_bulk(references, valid_time)


@router.get("/object", tags=["Objects"])
def get_object(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    reference: Reference = Depends(extract_reference),
):
    return octopoes.get_ooi(reference, valid_time)


@router.get("/objects/random", tags=["Objects"])
def list_random_objects(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    amount: int = 1,
    scan_level: Set[ScanLevel] = Query(DEFAULT_SCAN_LEVEL_FILTER),
):
    return octopoes.list_random_ooi(valid_time, amount, scan_level)


@router.delete("/", tags=["Objects"])
def delete_object(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    reference: Reference = Depends(extract_reference),
) -> None:
    octopoes.ooi_repository.delete(reference, valid_time)
    octopoes.commit()


@router.post("/objects/delete_many", tags=["Objects"])
def delete_many(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    references: List[Reference] = Depends(extract_references),
) -> None:
    for reference in references:
        octopoes.ooi_repository.delete(reference, valid_time)

    octopoes.commit()


@router.get("/tree", tags=["Objects"])
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


@router.get("/origins", tags=["Origins"])
def list_origins(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    source: Optional[Reference] = Query(None),
    result: Optional[Reference] = Query(None),
    task_id: Optional[uuid.UUID] = Query(None),
    origin_type: Optional[OriginType] = Query(None),
) -> List[Origin]:
    return octopoes.origin_repository.list(
        valid_time,
        task_id=task_id,
        source=source,
        result=result,
        origin_type=origin_type,
    )


@router.get("/origin_parameters", tags=["Origins"])
def list_origin_parameters(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    origin_id: Set[str] = Query(default=set()),
) -> List[OriginParameter]:
    return octopoes.origin_parameter_repository.list_by_origin(origin_id, valid_time)


@router.post("/observations", tags=["Origins"])
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
    octopoes.commit()


@router.post("/declarations", tags=["Origins"])
def save_declaration(
    declaration: ValidatedDeclaration,
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
    octopoes.commit()


# ScanProfile-related endpoints
@router.get("/scan_profiles", tags=["Scan Profiles"])
def list_scan_profiles(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    scan_profile_type: Optional[str] = Query(None),
) -> List[ScanProfileBase]:
    return octopoes.scan_profile_repository.list(scan_profile_type, valid_time)


@router.put("/scan_profiles", tags=["Scan Profiles"])
def save_scan_profile(
    scan_profile: ScanProfile = Body(discriminator="scan_profile_type"),
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_required_valid_time),
) -> None:
    try:
        old_scan_profile = octopoes.scan_profile_repository.get(scan_profile.reference, valid_time)
    except ObjectNotFoundException:
        old_scan_profile = None

    octopoes.scan_profile_repository.save(old_scan_profile, scan_profile, valid_time)
    octopoes.commit()


@router.post("/scan_profiles/save_many", tags=["Scan Profiles"])
def save_many(
    scan_profiles: List[ScanProfile],
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
) -> None:
    for scan_profile in scan_profiles:
        try:
            old_scan_profile = octopoes.scan_profile_repository.get(scan_profile.reference, valid_time)
        except ObjectNotFoundException:
            old_scan_profile = None

        octopoes.scan_profile_repository.save(old_scan_profile, scan_profile, valid_time)

    octopoes.commit()


@router.get("/scan_profiles/recalculate", tags=["Scan Profiles"])
def recalculate_scan_profiles(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_required_valid_time),
) -> None:
    octopoes.recalculate_scan_profiles(valid_time)
    octopoes.commit()


@router.get("/scan_profiles/inheritance", tags=["Scan Profiles"])
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


@router.get("/findings", tags=["Findings"])
def list_findings(
    exclude_muted: bool = True,
    only_muted: bool = False,
    offset=DEFAULT_OFFSET,
    limit=DEFAULT_LIMIT,
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
    severities: Set[RiskLevelSeverity] = Query(DEFAULT_SEVERITY_FILTER),
) -> Paginated[Finding]:
    return octopoes.ooi_repository.list_findings(
        severities,
        exclude_muted,
        only_muted,
        offset,
        limit,
        valid_time,
    )


@router.get("/findings/count_by_severity", tags=["Findings"])
def get_finding_type_count(
    octopoes: OctopoesService = Depends(octopoes_service),
    valid_time: datetime = Depends(extract_valid_time),
) -> Counter:
    return octopoes.ooi_repository.count_findings_by_severity(valid_time)


@router.post("/node", tags=["Node"])
def create_node(xtdb_session_: XTDBSession = Depends(xtdb_session)) -> None:
    try:
        xtdb_session_.client.create_node()
        xtdb_session_.commit()
    except NoMultinode:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="XTDB multinode is not set up for Octopoes."
        )
    except XTDBException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Creating node failed") from e


@router.delete("/node", tags=["Node"])
def delete_node(xtdb_session_: XTDBSession = Depends(xtdb_session)) -> None:
    try:
        xtdb_session_.client.delete_node()
        xtdb_session_.commit()
    except NoMultinode:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="XTDB multinode is not set up for Octopoes."
        )
    except XTDBException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Deleting node failed") from e


@router.post("/bits/recalculate", tags=["Bits"])
def recalculate_bits(octopoes: OctopoesService = Depends(octopoes_service)) -> int:
    inference_count = octopoes.recalculate_bits()
    octopoes.commit()

    return inference_count
