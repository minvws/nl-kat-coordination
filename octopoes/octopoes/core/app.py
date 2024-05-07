import logging

from amqp import AMQPError

from octopoes.config.settings import QUEUE_NAME_OCTOPOES, Settings
from octopoes.core.service import OctopoesService
from octopoes.events.manager import EventManager, get_rabbit_channel
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.repositories.origin_parameter_repository import XTDBOriginParameterRepository
from octopoes.repositories.origin_repository import XTDBOriginRepository
from octopoes.repositories.scan_profile_repository import XTDBScanProfileRepository
from octopoes.tasks.app import app as celery_app
from octopoes.xtdb.client import XTDBHTTPClient, XTDBSession

logger = logging.getLogger(__name__)


def get_xtdb_client(base_uri: str, client: str) -> XTDBHTTPClient:
    base_uri = base_uri.rstrip("/")

    return XTDBHTTPClient(f"{base_uri}/_xtdb", client)


def close_rabbit_channel(queue_uri: str):
    rabbit_channel = get_rabbit_channel(queue_uri)

    try:
        rabbit_channel.connection.close()
        logger.info("Closed connection to RabbitMQ")
    except AMQPError:
        logger.exception("Unable to close rabbit")


def bootstrap_octopoes(settings: Settings, client: str, xtdb_session: XTDBSession) -> OctopoesService:
    event_manager = EventManager(client, str(settings.queue_uri), celery_app, QUEUE_NAME_OCTOPOES)

    ooi_repository = XTDBOOIRepository(event_manager, xtdb_session)
    origin_repository = XTDBOriginRepository(event_manager, xtdb_session)
    origin_param_repository = XTDBOriginParameterRepository(event_manager, xtdb_session)
    scan_profile_repository = XTDBScanProfileRepository(event_manager, xtdb_session)

    octopoes = OctopoesService(ooi_repository, origin_repository, origin_param_repository, scan_profile_repository)

    return octopoes
