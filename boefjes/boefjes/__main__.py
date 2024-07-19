import json
import logging.config

import click

from boefjes.app import get_runtime_manager
from boefjes.config import settings
from boefjes.runtime_interfaces import WorkerManager

with settings.log_cfg.open() as f:
    logging.config.dictConfig(json.load(f))

logger = logging.getLogger(__name__)


@click.command()
@click.argument("worker_type", type=click.Choice([q.value for q in WorkerManager.Queue]))
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Log level",
    default="INFO",
)
def cli(worker_type: str, log_level: str):
    logger.setLevel(log_level)
    logger.info("Starting runtime for %s", worker_type)

    queue = WorkerManager.Queue(worker_type)
    runtime = get_runtime_manager(settings, queue, log_level)

    if worker_type == "boefje":
        import boefjes.api

        boefjes.api.run()

    runtime.run(queue)


if __name__ == "__main__":
    cli()
