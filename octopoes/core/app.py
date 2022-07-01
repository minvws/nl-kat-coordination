from typing import Tuple

import pika
from pika import BlockingConnection

from octopoes.config.settings import Settings, XTDBType
from octopoes.core.service import OctopoesService
from octopoes.events.manager import EventManager
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.repositories.origin_parameter_repository import XTDBOriginParameterRepository
from octopoes.repositories.origin_repository import XTDBOriginRepository
from octopoes.repositories.scan_profile_repository import XTDBScanProfileRepository
from octopoes.tasks.app import app as celery_app
from octopoes.xtdb.client import XTDBHTTPClient, XTDBSession


def get_xtdb_client(base_uri: str, client: str, xtdb_type: XTDBType) -> XTDBHTTPClient:
    parts = [base_uri]
    if client != "_dev":
        parts.append(client)
    parts.append(f"_{xtdb_type.value}")
    return XTDBHTTPClient("/".join(parts))


def bootstrap_octopoes(
    settings: Settings, client: str
) -> Tuple[OctopoesService, XTDBHTTPClient, XTDBSession, BlockingConnection]:
    xtdb_client = get_xtdb_client(settings.xtdb_uri, client, settings.xtdb_type)
    xtdb_session = XTDBSession(xtdb_client)

    rabbit_connection = pika.BlockingConnection(pika.URLParameters(settings.queue_uri))
    channel = rabbit_connection.channel()
    channel.queue_declare(queue="create_events", durable=True)

    event_manager = EventManager(client, celery_app, settings.queue_name_octopoes, channel)

    ooi_repository = XTDBOOIRepository(event_manager, xtdb_session, settings.xtdb_type)
    origin_repository = XTDBOriginRepository(event_manager, xtdb_session, settings.xtdb_type)
    origin_param_repository = XTDBOriginParameterRepository(event_manager, xtdb_session, settings.xtdb_type)
    scan_profile_repository = XTDBScanProfileRepository(event_manager, xtdb_session, settings.xtdb_type)

    octopoes = OctopoesService(ooi_repository, origin_repository, origin_param_repository, scan_profile_repository)

    return octopoes, xtdb_client, xtdb_session, rabbit_connection
