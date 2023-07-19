import timeit
import uuid
from datetime import datetime, timezone
from logging import config, getLogger
from pathlib import Path
from typing import Dict

import yaml
from celery.signals import worker_process_init, worker_process_shutdown
from pydantic import parse_obj_as

from octopoes.config.settings import Settings
from octopoes.connector.katalogus import KATalogusClientV1
from octopoes.core.app import bootstrap_octopoes, close_rabbit_channel, get_xtdb_client
from octopoes.events.events import EVENT_TYPE, DBEvent
from octopoes.events.manager import get_rabbit_channel
from octopoes.tasks.app import app
from octopoes.xtdb.client import XTDBSession

settings = Settings()
logger = getLogger(__name__)

try:
    with Path(settings.log_cfg).open() as log_config:
        config.dictConfig(yaml.safe_load(log_config))
        logger.info("Configured loggers with config: %s", settings.log_cfg)
except FileNotFoundError:
    logger.warning("No log config found at: %s", settings.log_cfg)


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    close_rabbit_channel(settings.queue_uri)


@worker_process_init.connect
def init_worker(**kwargs):
    """Set up one RabbitMQ connection and channel on worker startup"""
    get_rabbit_channel(settings.queue_uri)


@app.task(queue=settings.QUEUE_NAME_OCTOPOES)
def handle_event(event: Dict):
    parsed_event: DBEvent = parse_obj_as(EVENT_TYPE, event)

    session = XTDBSession(get_xtdb_client(settings.xtdb_uri, parsed_event.client, settings.xtdb_type))
    bootstrap_octopoes(settings, parsed_event.client, session).process_event(parsed_event)
    session.commit()


@app.task(queue=settings.QUEUE_NAME_OCTOPOES)
def schedule_scan_profile_recalculations():
    orgs = KATalogusClientV1(settings.katalogus_api).get_organisations()

    for org in orgs:
        app.send_task(
            "octopoes.tasks.tasks.recalculate_scan_profiles",
            (org,),
            queue=settings.QUEUE_NAME_OCTOPOES,
            task_id=str(uuid.uuid4()),
        )
        logger.info("Scheduled scan profile recalculation [org=%s]", org)


@app.task(queue=settings.QUEUE_NAME_OCTOPOES)
def recalculate_scan_profiles(org: str, *args, **kwargs):
    session = XTDBSession(get_xtdb_client(settings.xtdb_uri, org, settings.xtdb_type))
    octopoes = bootstrap_octopoes(settings, org, session)

    timer = timeit.default_timer()
    octopoes.recalculate_scan_profiles(datetime.now(timezone.utc))
    session.commit()

    logger.info(
        "Finished scan profile recalculation [org=%s] [dur=%.2fs]",
        org,
        timeit.default_timer() - timer,
    )
