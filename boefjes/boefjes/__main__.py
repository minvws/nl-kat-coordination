import json
import logging.config

import click
import structlog
from sqlalchemy.orm import sessionmaker

from boefjes.clients.scheduler_client import SchedulerAPIClient
from boefjes.config import Settings, settings
from boefjes.dependencies.plugins import PluginService
from boefjes.job_handler import CompositeBoefjeHandler, DockerBoefjeHandler, NormalizerHandler, bytes_api_client
from boefjes.local.runner import LocalNormalizerJobRunner
from boefjes.sql.config_storage import create_config_storage
from boefjes.sql.db import get_engine
from boefjes.sql.plugin_storage import create_plugin_storage
from boefjes.worker.boefje_handler import BoefjeHandler
from boefjes.worker.boefje_runner import LocalBoefjeJobRunner
from boefjes.worker.interfaces import Handler
from boefjes.worker.manager import SchedulerWorkerManager, WorkerManager
from boefjes.worker.repository import get_local_repository

with settings.log_cfg.open() as f:
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
            if settings.logging_format == "text"
            else structlog.processors.JSONRenderer()
        ),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def get_runtime_manager(settings: Settings, queue: WorkerManager.Queue, image: str | None) -> WorkerManager:
    local_repository = get_local_repository()

    session = sessionmaker(bind=get_engine())()
    plugin_service = PluginService(create_plugin_storage(session), create_config_storage(session), local_repository)
    scheduler_client = SchedulerAPIClient(plugin_service, str(settings.scheduler_api), image)

    if queue is WorkerManager.Queue.BOEFJES:
        item_handler = CompositeBoefjeHandler(
            BoefjeHandler(LocalBoefjeJobRunner(local_repository), bytes_api_client),
            DockerBoefjeHandler(scheduler_client, bytes_api_client),
        )
    else:
        item_handler = NormalizerHandler(
            LocalNormalizerJobRunner(local_repository), bytes_api_client, settings.scan_profile_whitelist
        )

    return SchedulerWorkerManager(
        item_handler, scheduler_client, settings.pool_size, settings.poll_interval, settings.worker_heartbeat
    )


@click.command()
@click.argument("queue", type=click.Choice([q.value for q in WorkerManager.Queue]))
@click.option("-i", "--image", type=str | None, default=None)
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), help="Log level", default="INFO")
def cli(queue: str, image: str | None, log_level: str) -> None:
    logger.setLevel(log_level)
    logger.info("Starting runtime for %s", queue)

    runtime = get_runtime_manager(settings, WorkerManager.Queue(queue), image)

    if queue == "boefje":
        import boefjes.api

        boefjes.api.run()

    runtime.run(WorkerManager.Queue(queue))


if __name__ == "__main__":
    cli()
