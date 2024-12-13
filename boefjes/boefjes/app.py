from sqlalchemy.orm import sessionmaker

from boefjes.clients.scheduler_client import SchedulerAPIClient
from boefjes.config import Settings
from boefjes.dependencies.plugins import PluginService
from boefjes.job_handler import (
    BoefjeHandler,
    CompositeBoefjeHandler,
    DockerBoefjeHandler,
    NormalizerHandler,
    bytes_api_client,
)
from boefjes.local.local import LocalBoefjeJobRunner, LocalNormalizerJobRunner
from boefjes.local.local_repository import get_local_repository
from boefjes.sql.config_storage import create_config_storage
from boefjes.sql.db import get_engine
from boefjes.sql.plugin_storage import create_plugin_storage
from boefjes.worker.interfaces import Handler
from boefjes.worker.manager import SchedulerWorkerManager, WorkerManager


def get_runtime_manager(settings: Settings, queue: WorkerManager.Queue) -> WorkerManager:
    local_repository = get_local_repository()

    session = sessionmaker(bind=get_engine())()
    plugin_service = PluginService(create_plugin_storage(session), create_config_storage(session), local_repository)
    scheduler_client = SchedulerAPIClient(plugin_service, str(settings.scheduler_api))

    item_handler: Handler
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
