from logging import getLogger, config
from typing import Dict

import yaml
from pydantic import parse_obj_as

from octopoes.config.settings import Settings
from octopoes.core.app import bootstrap_octopoes
from octopoes.events.events import EVENT_TYPE, DBEvent, CalculateScanLevelTask
from octopoes.models.exception import ObjectNotFoundException
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
def calculate_scan_profile(task: Dict):

    task = CalculateScanLevelTask.parse_obj(task)

    octopoes, _, session, rabbit_connection = bootstrap_octopoes(settings, task.client)

    try:
        ooi = octopoes.get_ooi(task.reference, task.valid_time)

        octopoes._calculate_scan_profile(ooi, ooi.scan_profile, task.valid_time)

        session.commit()
    except ObjectNotFoundException:
        ...
    finally:
        rabbit_connection.close()
