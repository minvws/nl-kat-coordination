import json
import logging.config
import os
from pathlib import Path

import click
import structlog

from .boefje_handler import BoefjeHandler
from .boefje_runner import LocalBoefjeJobRunner
from .client import BoefjeAPIClient
from .manager import SchedulerWorkerManager, WorkerManager
from .repository import get_local_repository

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
@click.option("-p", "--plugins", type=list[str] | None, default=None, help="A list of plugin ids to filter on.")
@click.option(
    "-l", "--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), help="Log level", default="INFO"
)
def cli(plugins: list[str] | None, log_level: str) -> None:
    logger.setLevel(log_level)
    logger.info("Starting runtime")

    base_url = os.getenv("BOEFJE_API")
    oci_image = os.getenv("OCI_IMAGE")
    plugins = os.getenv("PLUGINS", ",".join(plugins) if plugins else None).split(",")
    pool_size = int(os.getenv("POOL_SIZE", "2"))
    poll_interval = float(os.getenv("POLL_INTERVAL", "10.0"))
    heartbeat = float(os.getenv("WORKER_HEARTBEAT", "1.0"))

    if base_url is None:
        raise ValueError("An task API is needed for a worker setup. See the BOEFJE_API environment variable.")

    if oci_image is None:
        raise ValueError(
            "This environment has not been built properly: no OCI_IMAGE environment variable found. "
            "Please build the boefje image with this variable set to the oci image id."
        )

    outgoing_request_timeout = int(os.getenv("OUTGOING_REQUEST_TIMEOUT", "30"))

    local_repository = get_local_repository()
    boefje_api = BoefjeAPIClient(base_url, outgoing_request_timeout, [oci_image], plugins)
    handler = BoefjeHandler(LocalBoefjeJobRunner(local_repository), boefje_api)

    SchedulerWorkerManager(handler, boefje_api, pool_size, poll_interval, heartbeat).run(WorkerManager.Queue.BOEFJES)


if __name__ == "__main__":
    cli()
