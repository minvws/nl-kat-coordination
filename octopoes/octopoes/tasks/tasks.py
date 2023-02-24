import timeit
import uuid
from datetime import timezone, datetime
from logging import getLogger, config
from typing import Dict

import yaml
from pydantic import parse_obj_as

from octopoes.config.settings import Settings
from octopoes.connector.katalogus import KATalogusClientV1
from octopoes.core.app import bootstrap_octopoes
from octopoes.events.events import EVENT_TYPE, DBEvent
from octopoes.tasks.app import app

settings = Settings()
logger = getLogger(__name__)

try:
    with open(settings.log_cfg, "r") as log_config:
        config.dictConfig(yaml.safe_load(log_config))
        logger.info(f"Configured loggers with config: {settings.log_cfg}")
except FileNotFoundError:
    logger.warning(f"No log config found at: {settings.log_cfg}")


@app.task(queue=settings.queue_name_octopoes)
def handle_event(event: Dict):
    parsed_event: DBEvent = parse_obj_as(EVENT_TYPE, event)

    # bootstrap octopoes
    octopoes, _, session, rabbit_connection = bootstrap_octopoes(settings, parsed_event.client)

    # fire event
    octopoes.process_event(parsed_event)

    # teardown octopoes
    session.commit()
    rabbit_connection.close()


@app.task(queue=settings.queue_name_octopoes)
def schedule_scan_profile_recalculations():
    orgs = KATalogusClientV1(settings.katalogus_api).get_organisations()

    for org in orgs:
        app.send_task(
            "octopoes.tasks.tasks.recalculate_scan_profiles",
            (org,),
            queue=settings.queue_name_octopoes,
            task_id=str(uuid.uuid4()),
        )
        logger.info("Scheduled scan profile recalculation [org=%s]", org)


@app.task(queue=settings.queue_name_octopoes)
def recalculate_scan_profiles(org: str, *args, **kwargs):
    # bootstrap octopoes
    octopoes, _, session, rabbit_connection = bootstrap_octopoes(settings, org)

    # timer
    timer = timeit.default_timer()

    octopoes.recalculate_scan_profiles(datetime.now(timezone.utc))

    # teardown octopoes
    session.commit()
    rabbit_connection.close()

    logger.info("Finished scan profile recalculation [org=%s] [dur=%.2fs]", org, timeit.default_timer() - timer)
