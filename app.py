import logging
import os
from multiprocessing import Pool
from typing import Callable

import time

from celery import Celery
from requests import HTTPError as RequestHTTPError
from requests import ConnectionError
from urllib3.exceptions import HTTPError

from boefjes import celery_config
from boefjes.clients.scheduler_client import (
    SchedulerAPIClient,
    SchedulerClientInterface,
)
from boefjes.config import Settings
from boefjes.job_handler import BoefjeMetaHandler, NormalizerMetaHandler
from boefjes.runtime import ItemHandler, RuntimeManager, StopWorking

logger = logging.getLogger(__name__)


app = Celery()
app.config_from_object(celery_config)


class SchedulerRuntimeManager(RuntimeManager):
    def __init__(
        self,
        item_handler: ItemHandler,
        client_factory: Callable[[], SchedulerClientInterface],
        settings: Settings,
        log_level: str,  # TODO: (re)move?
    ):
        self.item_handler = item_handler
        self.client_factory = client_factory
        self.settings = settings

        logger.setLevel(log_level)

    def run(self, queue: RuntimeManager.Queue) -> None:
        logger.info(f"Creating worker pool for queue '{queue.value}'")
        pool_size = self.settings.pool_size

        with Pool(processes=pool_size) as pool:
            try:
                pool.starmap(
                    start_working,
                    [
                        (self.client_factory(), self.item_handler, self.settings, queue)
                        for _ in range(pool_size)
                    ],
                )
            except Exception as e:
                logger.exception("An error occurred")

            logger.info("Closing worker pool")


def start_working(
    scheduler_client: SchedulerClientInterface,
    item_handler: ItemHandler,
    settings: Settings,
    queue_to_handle: RuntimeManager.Queue,
) -> None:
    """
    This function runs in parallel and polls the scheduler for queues and jobs.
    Hence, it should catch most errors and give proper, granular feedback to the user.
    """

    logger.info(f"Started worker process [pid={os.getpid()}]")

    while True:
        try:
            queues = scheduler_client.get_queues()

            # We do not target a specific queue since we start one runtime for all organisations
            # and queue ids contain the organisation_id
            queues = [q for q in queues if q.id.startswith(queue_to_handle.value)]

            logger.debug(f"Found queues: {[queue.id for queue in queues]}")
        except (RequestHTTPError, HTTPError, ConnectionError):
            # Scheduler is having issues, so make not of it and try again
            logger.exception("Getting the queues from the scheduler failed")
            time.sleep(10 * settings.poll_interval)  # But not immediately

            continue

        for queue in queues:
            try:
                logger.info(f"Popping from queue {queue.id}")
                task = scheduler_client.pop_task(queue.id)
            except (RequestHTTPError, HTTPError, ConnectionError):
                logger.exception("Popping task from scheduler failed")
                time.sleep(10 * settings.poll_interval)  # But not immediately
                continue

            if not task:
                logger.info(f"Queue {queue.id} empty")
                continue

            try:
                logger.info(f"Handling task[{task.item.id}]")
                item_handler.handle(task.item)
            except StopWorking:
                logger.info("Stopping worker...")
                break
            except:
                logger.exception("An error occurred handling a scheduler item")

        time.sleep(settings.poll_interval)


class CeleryRuntimeManager(RuntimeManager):
    def __init__(self, settings: Settings, log_level: str):
        self.settings = settings
        self.log_level = log_level

    def run(self, queue: RuntimeManager.Queue) -> None:
        queue_names = {
            RuntimeManager.Queue.BOEFJES.value: self.settings.queue_name_boefjes,
            RuntimeManager.Queue.NORMALIZERS.value: self.settings.queue_name_normalizers,
        }

        app.worker_main(
            [
                "--app",
                "boefjes.tasks",
                "worker",
                "--loglevel",
                self.log_level,
                "--events",
                "--queues",
                [queue_names.get(queue.value)],
                "--hostname",
                f"{queue.value}@%h",
            ]
        )


def get_runtime_manager(
    settings: Settings, queue: RuntimeManager.Queue, log_level: str
) -> RuntimeManager:
    if settings.use_scheduler:
        # Not a lambda since multiprocessing tries and fails to pickle lambda's
        def client_factory():
            return SchedulerAPIClient(settings.scheduler_api)

        item_handler = (
            BoefjeMetaHandler()
            if queue is RuntimeManager.Queue.BOEFJES
            else NormalizerMetaHandler()
        )

        return SchedulerRuntimeManager(
            item_handler,
            # Do not share a session between workers
            client_factory,
            settings,
            log_level,
        )

    return CeleryRuntimeManager(settings, log_level)
