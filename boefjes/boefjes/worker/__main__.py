import json
import logging.config
import os
from pathlib import Path

import click
import structlog

from .boefje_handler import BoefjeHandler
from .boefje_runner import LocalBoefjeJobRunner
from .repository import get_local_repository
from .manager import WorkerManager, SchedulerWorkerManager

logging_format = os.getenv("LOGGING_FORMAT", "text")
log_cfg = Path(os.getenv("LOG_CFG", "logging.json"))

with log_cfg.open() as f:
    logging.config.dictConfig(json.load(f))

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper("iso", utc=False),
        (
            structlog.dev.ConsoleRenderer(colors=True, pad_level=False)
            if logging_format == "text"
            else structlog.processors.JSONRenderer()
        ),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@click.command()
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), help="Log level", default="INFO")
def cli(log_level: str) -> None:
    logger.setLevel(log_level)
    logger.info("Starting runtime")

    local_repository = get_local_repository()

    scheduler = None  # TODO: boefje API proxy
    boefje_storage = None  # TODO: boefje API proxy

    handler = BoefjeHandler(LocalBoefjeJobRunner(local_repository), boefje_storage)
    pool_size = int(os.getenv("POOL_SIZE", "2"))
    poll_interval = float(os.getenv("POLL_INTERVAL", "10.0"))
    heartbeat = float(os.getenv("WORKER_HEARTBEAT", "1.0"))

    SchedulerWorkerManager(handler, scheduler, pool_size, poll_interval, heartbeat).run(WorkerManager.Queue.BOEFJES)


if __name__ == "__main__":
    cli()
