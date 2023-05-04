from typing import Optional, Tuple

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


def bootstrap_octopoes(
    settings: Settings, client: str, xtdb_session: Optional[XTDBSession] = None
) -> Tuple[OctopoesService, XTDBHTTPClient, XTDBSession, BlockingConnection]:
    xtdb_client = get_xtdb_client(settings.xtdb_uri, client, settings.xtdb_type)
    if xtdb_session is None:
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
