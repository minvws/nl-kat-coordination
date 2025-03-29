import timeit
import uuid
from datetime import datetime, timezone
from logging import config
from pathlib import Path
from typing import Any

import structlog
import yaml
from celery.signals import worker_process_init, worker_process_shutdown
from celery.utils.log import get_task_logger
from httpx import HTTPError
from pydantic import TypeAdapter

from octopoes.config.settings import QUEUE_NAME_OCTOPOES, Settings
from octopoes.connector.katalogus import KATalogusClient
from octopoes.core.app import bootstrap_octopoes, close_rabbit_channel, get_xtdb_client
from octopoes.events.events import DBEvent, DBEventType
from octopoes.events.manager import get_rabbit_channel
from octopoes.tasks.app import app
from octopoes.xtdb.client import XTDBSession

settings = Settings()
logger = structlog.get_logger(__name__)

try:
    with Path(settings.log_cfg).open() as log_config:
        config.dictConfig(yaml.safe_load(log_config))
        logger.info("Configured loggers with config: %s", settings.log_cfg)
except FileNotFoundError:
    logger.warning("No log config found at: %s", settings.log_cfg)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper("iso", utc=False),
        (
            structlog.dev.ConsoleRenderer(
                colors=True, pad_level=False, exception_formatter=structlog.dev.plain_traceback
            )
            if settings.logging_format == "text"
            else structlog.processors.JSONRenderer()
        ),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    close_rabbit_channel(str(settings.queue_uri))


@worker_process_init.connect
def init_worker(**kwargs):
    """Set up one RabbitMQ connection and channel on worker startup"""
    get_rabbit_channel(str(settings.queue_uri))


log = get_task_logger(__name__)


@app.task(queue=QUEUE_NAME_OCTOPOES)
def handle_event(event: dict) -> None:
    try:
        parsed_event: DBEvent = TypeAdapter(DBEventType).validate_python(event)

        session = XTDBSession(get_xtdb_client(str(settings.xtdb_uri), parsed_event.client))
        bootstrap_octopoes(settings, parsed_event.client, session).process_event(parsed_event)
        session.commit()
    except Exception:
        logger.exception("Failed to handle event: %s", event)
        raise


@app.task(queue=QUEUE_NAME_OCTOPOES)
def schedule_scan_profile_recalculations():
    try:
        orgs = KATalogusClient(str(settings.katalogus_api)).get_organisations()
    except HTTPError:
        logger.exception("Failed getting organizations")
        raise

    for org in orgs:
        app.send_task(
            "octopoes.tasks.tasks.recalculate_scan_profiles",
            (org,),
            queue=QUEUE_NAME_OCTOPOES,
            task_id=str(uuid.uuid4()),
        )
        logger.info("Scheduled scan profile recalculation [org=%s]", org)


@app.task(queue=QUEUE_NAME_OCTOPOES)
def recalculate_scan_profiles(org: str, *args: Any, **kwargs: Any) -> None:
    session = XTDBSession(get_xtdb_client(str(settings.xtdb_uri), org))
    octopoes = bootstrap_octopoes(settings, org, session)

    timer = timeit.default_timer()

    try:
        octopoes.recalculate_scan_profiles(datetime.now(timezone.utc))
        session.commit()
    except Exception:
        logger.exception("Failed recalculating scan profiles [org=%s] [dur=%.2fs]", org, timeit.default_timer() - timer)

    logger.info("Finished scan profile recalculation [org=%s] [dur=%.2fs]", org, timeit.default_timer() - timer)
