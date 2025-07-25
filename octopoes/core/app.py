import structlog
from django.conf import settings

from octopoes.core.service import OctopoesService
from octopoes.events.manager import EventManager
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.repositories.origin_parameter_repository import XTDBOriginParameterRepository
from octopoes.repositories.origin_repository import XTDBOriginRepository
from octopoes.repositories.scan_profile_repository import XTDBScanProfileRepository
from octopoes.xtdb.client import XTDBHTTPClient, XTDBSession
from tasks.celery import app as celery_app

logger = structlog.get_logger(__name__)


def get_xtdb_client(base_uri: str, client: str) -> XTDBHTTPClient:
    base_uri = base_uri.rstrip("/")

    return XTDBHTTPClient(f"{base_uri}/_xtdb", client)


def bootstrap_octopoes(client: str, xtdb_session: XTDBSession) -> OctopoesService:
    event_manager = EventManager(client, celery_app, settings.QUEUE_NAME_OCTOPOES)

    origin_repository = XTDBOriginRepository(event_manager, xtdb_session)
    origin_param_repository = XTDBOriginParameterRepository(event_manager, xtdb_session)
    scan_profile_repository = XTDBScanProfileRepository(event_manager, xtdb_session)
    ooi_repository = XTDBOOIRepository(event_manager, xtdb_session, scan_profile_repository)

    if settings.GATHER_BIT_METRICS:
        return OctopoesService(
            ooi_repository, origin_repository, origin_param_repository, scan_profile_repository, xtdb_session
        )
    else:
        return OctopoesService(ooi_repository, origin_repository, origin_param_repository, scan_profile_repository)
