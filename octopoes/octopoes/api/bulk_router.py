import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends

from octopoes.api.router import extract_valid_time
from octopoes.api.router import settings as extract_settings
from octopoes.config.settings import QUEUE_NAME_OCTOPOES, Settings
from octopoes.core.app import get_xtdb_client
from octopoes.events.manager import EventManager
from octopoes.models.ooi.reports import HydratedReport
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.tasks.app import app as celery_app
from octopoes.xtdb.client import XTDBSession

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/reports", tags=["Reports"])
def list_reports(
    reports_filters: list[tuple[str, uuid.UUID]],
    settings_: Settings = Depends(extract_settings),
    valid_time: datetime = Depends(extract_valid_time),
) -> dict[uuid.UUID, HydratedReport]:
    """
    An efficient endpoint for getting reports across organizations
    """

    # The reason for creating the event_manager do this in the loop is the '_try_connect()' call in the __init__
    # possibly slowing this down, while this API was introduced to improve performance. Simply reusing it for all
    # clients works because the event manager is only used in callbacks triggered on a `commit()`, while these queries
    # are read-only and hence don't need a `commit()` as no events would be triggered. (A cleaner solution would perhaps
    #  be to extract an interface and pass a new NullManager.)
    event_manager = EventManager("null", str(settings_.queue_uri), celery_app, QUEUE_NAME_OCTOPOES)

    # The xtdb_http_client is also created outside the loop and the `_client` property changed inside the loop instead,
    # to reuse the httpx Session for all requests.
    xtdb_http_client = get_xtdb_client(str(settings_.xtdb_uri), "")

    reports = {}

    for client, recipe_id in reports_filters:
        xtdb_http_client.client = client
        ooi_repository = XTDBOOIRepository(event_manager, XTDBSession(xtdb_http_client))

        for report in ooi_repository.list_reports(valid_time, 0, 1, recipe_id, ignore_count=True).items:
            reports[recipe_id] = report

    return reports
