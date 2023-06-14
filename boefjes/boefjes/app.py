import logging
import os
import signal
import time
from multiprocessing import Process
from typing import Callable, List

from pydantic import ValidationError
from requests import HTTPError

from boefjes.clients.scheduler_client import (
    QueuePrioritizedItem,
    SchedulerAPIClient,
    SchedulerClientInterface,
    TaskStatus,
)
from boefjes.config import Settings
from boefjes.job_handler import BoefjeHandler, NormalizerHandler
from boefjes.katalogus.local_repository import get_local_repository
from boefjes.local import LocalBoefjeJobRunner, LocalNormalizerJobRunner
from boefjes.runtime_interfaces import Handler, WorkerManager

logger = logging.getLogger(__name__)


class SchedulerWorkerManager(WorkerManager):
    def __init__(
        self,
        item_handler: Handler,
        client_factory: Callable[[], SchedulerClientInterface],
        settings: Settings,
        log_level: str,  # TODO: (re)move?
    ):
        self.item_handler = item_handler
        self.client_factory = client_factory
        self.settings = settings
        self.processes: List[Process] = []

        logger.setLevel(log_level)

    def run(self, queue: WorkerManager.Queue) -> None:
        logger.info("Creating worker pool for queue '%s'", queue.value)
        self.start_workers(queue)

        while True:
            self._monitor_processes(queue)
            time.sleep(self.settings.poll_interval)

    def start_workers(self, queue):
        self.processes = [self._create_worker_process(queue) for _ in range(self.settings.pool_size)]

    def _monitor_processes(self, queue: WorkerManager.Queue):
        for i, process in enumerate(self.processes):
            if process.is_alive():
                continue

            logger.warning("Process[index=%s, pid=%s] was terminated, recreating...", i, process.pid)
            self.processes[i] = self._create_worker_process(queue)

    def _create_worker_process(self, queue: WorkerManager.Queue) -> Process:
        args = self.client_factory(), self.item_handler, self.settings, queue
        proc = Process(target=start_working, args=args)
        proc.start()

        return proc


def start_working(
    scheduler_client: SchedulerClientInterface,
    item_handler: Handler,
    settings: Settings,
    queue_to_handle: WorkerManager.Queue,
) -> None:
    """
    This function runs in parallel and polls the scheduler for queues and jobs.
    Hence, it should catch most errors and give proper, granular feedback to the user.
    """

    logger.info("Started worker process [pid=%d]", os.getpid())

    while True:
        try:
            queues = scheduler_client.get_queues()
        except HTTPError:
            # Scheduler is having issues, so make note of it and try again
            logger.exception("Getting the queues from the scheduler failed")
            time.sleep(10 * settings.poll_interval)  # But not immediately
            continue

        # We do not target a specific queue since we start one runtime for all organisations
        # and queue ids contain the organisation_id
        queues = [q for q in queues if q.id.startswith(queue_to_handle.value)]

        logger.debug("Found queues: %s", [queue.id for queue in queues])

        all_queues_empty = True

        for queue in queues:
            logger.debug("Popping from queue %s", queue.id)

            try:
                p_item = scheduler_client.pop_item(queue.id)
            except (HTTPError, ValidationError):
                logger.exception("Popping task from scheduler failed, sleeping 10 seconds")
                time.sleep(10)
                continue

            if not p_item:
                logger.debug("Queue %s empty", queue.id)
                continue

            all_queues_empty = False

            logger.info("Handling task[%s]", p_item.data.id)
            status = TaskStatus.FAILED

            try:
                subp = Process(
                    target=_log_handle,
                    args=(
                        item_handler,
                        p_item,
                    ),
                )
                subp.start()
                subp.join(timeout=settings.max_plugin_runtime)

                if subp.is_alive():
                    subp.terminate()
                    subp.join()

                if subp.exitcode == 0:
                    status = TaskStatus.COMPLETED
                else:
                    logger.warning(
                        "An error occurred handling scheduler item: Process ended [pid=%s, %s]",
                        subp.pid,
                        _format_exit_code(subp.exitcode),
                    )
                    status = TaskStatus.FAILED

                subp.close()
            except:  # noqa
                logger.exception("Exiting worker...")
                raise
            finally:
                logger.info("Patching scheduler task[id=%s] to %s", p_item.data.id, status.value)

                try:
                    scheduler_client.patch_task(str(p_item.id), status)
                    logger.info("Set task status to %s in the scheduler for task[id=%s]", status, p_item.data.id)
                except HTTPError:
                    logger.exception("Could not patch scheduler task to %s", status.value)

        if all_queues_empty:
            logger.debug("All queues empty, sleeping %f seconds", settings.poll_interval)
            time.sleep(settings.poll_interval)


def _format_exit_code(exitcode: int) -> str:
    if exitcode >= 0:
        return f"exitcode={exitcode}"

    return f"signal={signal.Signals(-exitcode).name}"


def _log_handle(item_handler: Handler, prioritized_item: QueuePrioritizedItem):
    try:
        item_handler.handle(prioritized_item.data)
    except:  # noqa
        logger.exception("An error occurred handling scheduler item[id=%s]", prioritized_item.data.id)
        raise


def get_runtime_manager(settings: Settings, queue: WorkerManager.Queue, log_level: str) -> WorkerManager:
    # Not a lambda since multiprocessing tries and fails to pickle lambda's
    def client_factory():
        return SchedulerAPIClient(settings.scheduler_api)

    if queue is WorkerManager.Queue.BOEFJES:
        item_handler = BoefjeHandler(LocalBoefjeJobRunner(get_local_repository()), get_local_repository())
    else:
        item_handler = NormalizerHandler(LocalNormalizerJobRunner(get_local_repository()))

    return SchedulerWorkerManager(
        item_handler,
        client_factory,  # Do not share a session between workers
        settings,
        log_level,
    )
