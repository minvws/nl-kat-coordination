import logging
import multiprocessing as mp
import os
import signal
import sys
import time
from typing import Dict, List, Optional, Tuple

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
        scheduler_client: SchedulerClientInterface,
        settings: Settings,
        log_level: str,  # TODO: (re)move?
    ):
        self.item_handler = item_handler
        self.scheduler_client = scheduler_client
        self.settings = settings

        manager = mp.Manager()

        self.task_queue = manager.Queue()  # multiprocessing.Queue() will not work on macOS, see mp.Queue.qsize()
        self.handling_tasks = manager.dict()
        self.workers = []

        logger.setLevel(log_level)

        self.exited = False

    def run(self, queue_type: WorkerManager.Queue) -> None:
        logger.info("Created worker pool for queue '%s'", queue_type.value)

        self.workers = [
            mp.Process(target=_start_working, args=self._worker_args()) for _ in range(self.settings.pool_size)
        ]
        for worker in self.workers:
            worker.start()

        signal.signal(signal.SIGINT, lambda signum, _: self.exit(queue_type, signum))
        signal.signal(signal.SIGTERM, lambda signum, _: self.exit(queue_type, signum))

        while True:
            try:
                self._check_workers()
                self._fill_queue(self.task_queue, queue_type)
            except Exception as e:  # noqa
                logger.exception("Unhandled Exception:")
                logger.info("Continuing worker...")
                continue
            except:  # noqa
                # Calling sys.exit() in self.exit() will raise SystemExit. We
                # should only log the exception and call self.exit() when the
                # exception is caused by something else and self.exit() hasn't
                # been called yet.
                if not self.exited:
                    logger.exception("Exiting worker...")
                    self.exit(queue_type)

                raise

    def _fill_queue(self, task_queue: mp.Queue, queue_type: WorkerManager.Queue):
        if task_queue.qsize() > self.settings.pool_size:
            time.sleep(self.settings.worker_heartbeat)
            return

        try:
            queues = self.scheduler_client.get_queues()
        except HTTPError:
            # Scheduler is having issues, so make note of it and try again
            logger.exception("Getting the queues from the scheduler failed")
            time.sleep(10 * self.settings.poll_interval)  # But not immediately
            return

        # We do not target a specific queue since we start one runtime for all organisations
        # and queue ids contain the organisation_id
        queues = [q for q in queues if q.id.startswith(queue_type.value)]

        logger.debug("Found queues: %s", [queue.id for queue in queues])

        all_queues_empty = True

        for queue_type in queues:
            logger.debug("Popping from queue %s", queue_type.id)

            try:
                p_item = self.scheduler_client.pop_item(queue_type.id)
            except (HTTPError, ValidationError):
                logger.exception("Popping task from scheduler failed, sleeping 10 seconds")
                time.sleep(10)
                continue

            if not p_item:
                logger.debug("Queue %s empty", queue_type.id)
                continue

            all_queues_empty = False

            logger.info("Handling task[%s]", p_item.data.id)

            try:
                task_queue.put(p_item)
                logger.info("Dispatched task[%s]", p_item.data.id)
            except:  # noqa
                logger.exception("Exiting worker...")
                logger.info("Patching scheduler task[id=%s] to %s", p_item.data.id, TaskStatus.FAILED.value)

                try:
                    self.scheduler_client.patch_task(p_item.id, TaskStatus.FAILED)
                    logger.info(
                        "Set task status to %s in the scheduler for task[id=%s]", TaskStatus.FAILED, p_item.data.id
                    )
                except HTTPError:
                    logger.exception("Could not patch scheduler task to %s", TaskStatus.FAILED.value)

                raise

        if all_queues_empty:
            logger.debug("All queues empty, sleeping %f seconds", self.settings.poll_interval)
            time.sleep(self.settings.poll_interval)

    def _check_workers(self) -> None:
        new_workers = []

        for worker in self.workers:
            if not worker._closed and worker.is_alive():
                new_workers.append(worker)
                continue

            logger.warning(
                "Worker[pid=%s, %s] not alive, creating new worker...", worker.pid, _format_exit_code(worker.exitcode)
            )

            if not worker._closed:  # Closed workers do not have a pid, so cleaning up would fail
                self._cleanup_pending_worker_task(worker)
                worker.close()

            new_worker = mp.Process(target=_start_working, args=self._worker_args())
            new_worker.start()
            new_workers.append(new_worker)

        self.workers = new_workers

    def _cleanup_pending_worker_task(self, worker: mp.Process) -> None:
        if worker.pid not in self.handling_tasks:
            logger.debug("No pending task found for Worker[pid=%s, %s]", worker.pid, _format_exit_code(worker.exitcode))
            return

        handling_task_id = self.handling_tasks[worker.pid]

        try:
            task = self.scheduler_client.get_task(handling_task_id)

            if task.status is TaskStatus.DISPATCHED:
                try:
                    self.scheduler_client.patch_task(task.id, TaskStatus.FAILED)
                    logger.warning("Set status to failed in the scheduler for task[id=%s]", handling_task_id)
                except HTTPError:
                    logger.exception("Could not patch scheduler task to failed")
        except HTTPError:
            logger.exception("Could not get scheduler task[id=%s]", handling_task_id)

    def _worker_args(self) -> Tuple:
        return self.task_queue, self.item_handler, self.scheduler_client, self.handling_tasks

    def exit(self, queue_type: WorkerManager.Queue, signum: Optional[int] = None):
        try:
            if signum:
                logger.info("Received %s, exiting", signal.Signals(signum).name)

            if not self.task_queue.empty():
                items: List[QueuePrioritizedItem] = [self.task_queue.get() for _ in range(self.task_queue.qsize())]

                for p_item in items:
                    try:
                        self.scheduler_client.push_item(queue_type.value, p_item)
                    except HTTPError:
                        logger.exception("Rescheduling task failed[id=%s]", p_item.id)

            killed_workers = []

            for worker in self.workers:  # Send all signals before joining, speeding up shutdowns
                if not worker._closed and worker.is_alive():
                    worker.kill()
                    killed_workers.append(worker)

            for worker in killed_workers:
                worker.join()
                self._cleanup_pending_worker_task(worker)
                worker.close()
        finally:
            self.exited = True
            # If we are called from the main run loop we are already in the
            # process of exiting, so we only need to call sys.exit() in the
            # signal handler.
            if signum:
                sys.exit()


def _format_exit_code(exitcode: int) -> str:
    if exitcode >= 0:
        return f"exitcode={exitcode}"

    return f"signal={signal.Signals(-exitcode).name}"


def _start_working(
    task_queue: mp.Queue,
    handler: Handler,
    scheduler_client: SchedulerClientInterface,
    handling_tasks: Dict[int, str],
):
    logger.info("Started listening for tasks from worker[pid=%s]", os.getpid())

    while True:
        p_item = task_queue.get()
        status = TaskStatus.FAILED
        handling_tasks[os.getpid()] = str(p_item.id)

        try:
            handler.handle(p_item.data)
            status = TaskStatus.COMPLETED
        except Exception:  # noqa
            logger.exception("An error occurred handling scheduler item[id=%s]", p_item.data.id)
        except:  # noqa
            logger.exception("An unhandled error occurred handling scheduler item[id=%s]", p_item.data.id)
            raise
        finally:
            try:
                scheduler_client.patch_task(p_item.id, status)  # Note: implicitly, we have p_item.id == task_id
                logger.info("Set status to %s in the scheduler for task[id=%s]", status, p_item.data.id)
            except HTTPError:
                logger.exception("Could not patch scheduler task to %s", status.value)


def get_runtime_manager(settings: Settings, queue: WorkerManager.Queue, log_level: str) -> WorkerManager:
    local_repository = get_local_repository()
    if queue is WorkerManager.Queue.BOEFJES:
        item_handler = BoefjeHandler(LocalBoefjeJobRunner(local_repository), local_repository)
    else:
        item_handler = NormalizerHandler(LocalNormalizerJobRunner(local_repository))

    return SchedulerWorkerManager(
        item_handler,
        SchedulerAPIClient(settings.scheduler_api),  # Do not share a session between workers
        settings,
        log_level,
    )
