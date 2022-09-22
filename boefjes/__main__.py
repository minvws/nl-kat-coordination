import json
import logging.config

import click

from boefjes.app import get_runtime_manager
from boefjes.runtime import RuntimeManager
from boefjes.config import settings

with open(settings.log_cfg, "r") as f:
    logging.config.dictConfig(json.load(f))

logger = logging.getLogger(__name__)


@click.command()
@click.argument(
    "worker_type", type=click.Choice([q.value for q in RuntimeManager.Queue])
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Log level",
    default="INFO",
)
def cli(worker_type: str, log_level: str):
    logger.setLevel(log_level)
    logger.info(f"Starting runtime for {worker_type}")

    queue = RuntimeManager.Queue(worker_type)
    runtime = get_runtime_manager(settings, queue, log_level)
    runtime.run(queue)


if __name__ == "__main__":
    cli()
