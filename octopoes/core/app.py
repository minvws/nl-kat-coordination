import structlog

from openkat.settings import QUEUE_NAME_OCTOPOES, GATHER_BIT_METRICS
from octopoes.core.service import OctopoesService
from octopoes.events.manager import EventManager
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.repositories.origin_parameter_repository import XTDBOriginParameterRepository
from octopoes.repositories.origin_repository import XTDBOriginRepository
from octopoes.repositories.scan_profile_repository import XTDBScanProfileRepository
from octopoes.xtdb.client import XTDBHTTPClient, XTDBSession
from openkat.celery import app as celery_app

logger = structlog.get_logger(__name__)


def get_xtdb_client(base_uri: str, client: str) -> XTDBHTTPClient:
    base_uri = base_uri.rstrip("/")

    return XTDBHTTPClient(f"{base_uri}/_xtdb", client)


def bootstrap_octopoes(client: str, xtdb_session: XTDBSession) -> OctopoesService:
    event_manager = EventManager(client, celery_app, QUEUE_NAME_OCTOPOES)

    origin_repository = XTDBOriginRepository(event_manager, xtdb_session)
    origin_param_repository = XTDBOriginParameterRepository(event_manager, xtdb_session)
    scan_profile_repository = XTDBScanProfileRepository(event_manager, xtdb_session)
    ooi_repository = XTDBOOIRepository(event_manager, xtdb_session, scan_profile_repository)

    if GATHER_BIT_METRICS:
        return OctopoesService(
            ooi_repository, origin_repository, origin_param_repository, scan_profile_repository, xtdb_session
        )
    else:
        return OctopoesService(ooi_repository, origin_repository, origin_param_repository, scan_profile_repository)
