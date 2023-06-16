import logging
import threading

import pika
from amqp import AMQPError
from pika.adapters.blocking_connection import BlockingChannel

from octopoes.config.settings import Settings, XTDBType
from octopoes.core.service import OctopoesService
from octopoes.events.manager import EventManager
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.repositories.origin_parameter_repository import XTDBOriginParameterRepository
from octopoes.repositories.origin_repository import XTDBOriginRepository
from octopoes.repositories.scan_profile_repository import XTDBScanProfileRepository
from octopoes.tasks.app import app as celery_app
from octopoes.xtdb.client import XTDBHTTPClient, XTDBSession

logger = logging.getLogger(__name__)


def get_xtdb_client(base_uri: str, client: str, xtdb_type: XTDBType) -> XTDBHTTPClient:
    """Base URL setup:
            - Xtdb-multinode: "{base_uri}/_xtdb/{client}"
            - Old development setup: "{base_uri}/{_crux|_xtdb}"
            - Old production setup: client proxy & "{base_uri}/{client}/{_crux|_xtdb}"

    Before we had xtdb-multinode we supported multiple organizations by running multiple XTDB with a reverse proxy in
    front. This code can be removed once we no longer support that setup.
    """

    if xtdb_type == XTDBType.XTDB_MULTINODE:
        return XTDBHTTPClient(f"{base_uri}/_xtdb", client, multinode=True)

    if client != "_dev":
        return XTDBHTTPClient(f"{base_uri}/{client}/_{xtdb_type.value}", client)

    return XTDBHTTPClient(f"{base_uri}/_{xtdb_type.value}", client)


thread_local = threading.local()


def get_rabbit_channel(queue_uri: str) -> BlockingChannel:
    try:
        return thread_local.rabbit_channel
    except AttributeError:
        connection = pika.BlockingConnection(pika.URLParameters(queue_uri))
        logger.info("Connected to RabbitMQ")

        thread_local.rabbit_channel = connection.channel()
        thread_local.rabbit_channel.queue_declare(queue="create_events", durable=True)

        return thread_local.rabbit_channel


def close_rabbit_channel(queue_uri: str):
    rabbit_channel = get_rabbit_channel(queue_uri)

    try:
        rabbit_channel.connection.close()
        logger.info("Closed connection to RabbitMQ")
    except AMQPError:
        logger.exception("Unable to close rabbit")
        pass


def bootstrap_octopoes(settings: Settings, client: str, xtdb_session: XTDBSession) -> OctopoesService:
    event_manager = EventManager(
        client, celery_app, settings.queue_name_octopoes, get_rabbit_channel(settings.queue_uri)
    )

    ooi_repository = XTDBOOIRepository(event_manager, xtdb_session, settings.xtdb_type)
    origin_repository = XTDBOriginRepository(event_manager, xtdb_session, settings.xtdb_type)
    origin_param_repository = XTDBOriginParameterRepository(event_manager, xtdb_session, settings.xtdb_type)
    scan_profile_repository = XTDBScanProfileRepository(event_manager, xtdb_session, settings.xtdb_type)

    octopoes = OctopoesService(ooi_repository, origin_repository, origin_param_repository, scan_profile_repository)

    return octopoes
