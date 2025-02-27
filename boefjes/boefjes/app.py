import multiprocessing
import os
import signal
import sys
import time
from multiprocessing.context import ForkContext
from multiprocessing.process import BaseProcess
from queue import Queue

import structlog
from httpx import HTTPError
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from boefjes.clients.scheduler_client import SchedulerAPIClient, SchedulerClientInterface, Task, TaskStatus
from boefjes.config import Settings
from boefjes.dependencies.plugins import PluginService
from boefjes.job_handler import BoefjeHandler, NormalizerHandler, bytes_api_client
from boefjes.local import LocalBoefjeJobRunner, LocalNormalizerJobRunner
from boefjes.local_repository import get_local_repository
from boefjes.runtime_interfaces import Handler, WorkerManager
from boefjes.sql.config_storage import create_config_storage
from boefjes.sql.db import get_engine
from boefjes.sql.plugin_storage import create_plugin_storage

logger = structlog.get_logger(__name__)
ctx: ForkContext = multiprocessing.get_context("fork")


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

        manager = ctx.Manager()

        self.task_queue = manager.Queue()  # multiprocessing.Queue() will not work on macOS, see mp.Queue.qsize()
        self.handling_tasks = manager.dict()
        self.workers: list[BaseProcess] = []

        logger.setLevel(log_level)

        self.exited = False

    def run(self, queue_type: WorkerManager.Queue) -> None:
        logger.info("Created worker pool for queue '%s'", queue_type.value)

        self.workers = [
            ctx.Process(target=_start_working, args=self._worker_args()) for _ in range(self.settings.pool_size)
        ]
        for worker in self.workers:
            worker.start()

        signal.signal(signal.SIGINT, lambda signum, _: self.exit(signum))
        signal.signal(signal.SIGTERM, lambda signum, _: self.exit(signum))

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
                    self.exit()

                raise

    def _fill_queue(self, task_queue: Queue, queue_type: WorkerManager.Queue) -> None:
        if task_queue.qsize() > self.settings.pool_size:
            time.sleep(self.settings.worker_heartbeat)
            return

        logger.debug("Popping from queue %s", queue_type.value)

        try:
            p_item = self.scheduler_client.pop_item(queue_type.value)
        except (HTTPError, ValidationError):
            logger.exception("Popping task from scheduler failed, sleeping 10 seconds")
            time.sleep(self.settings.worker_heartbeat)
            return

        if p_item is None:
            time.sleep(self.settings.worker_heartbeat)
            return

        logger.info("Handling task[%s]", p_item.data.id)

        try:
            task_queue.put(p_item)
            logger.info("Dispatched task[%s]", p_item.data.id)
        except:  # noqa
            logger.exception("Exiting worker...")
            logger.info("Patching scheduler task[id=%s] to %s", p_item.data.id, TaskStatus.FAILED.value)

            try:
                self.scheduler_client.patch_task(p_item.id, TaskStatus.FAILED)
                logger.info("Set task status to %s in the scheduler for task[id=%s]", TaskStatus.FAILED, p_item.data.id)
            except HTTPError:
                logger.exception("Could not patch scheduler task to %s", TaskStatus.FAILED.value)

    def _check_workers(self) -> None:
        new_workers = []

        for worker in self.workers:
            closed = False

            try:
                if worker.is_alive():
                    new_workers.append(worker)
                    continue
            except ValueError:
                closed = True  # worker is closed, so we create a new one

            logger.warning(
                "Worker[pid=%s, %s] not alive, creating new worker...", worker.pid, _format_exit_code(worker.exitcode)
            )

            if not closed:  # Closed workers do not have a pid, so cleaning up would fail
                self._cleanup_pending_worker_task(worker)
                worker.close()

            new_worker = ctx.Process(target=_start_working, args=self._worker_args())
            new_worker.start()
            new_workers.append(new_worker)

        self.workers = new_workers

    def _cleanup_pending_worker_task(self, worker: BaseProcess) -> None:
        if worker.pid not in self.handling_tasks:
            logger.debug("No pending task found for Worker[pid=%s, %s]", worker.pid, _format_exit_code(worker.exitcode))
            return

        handling_task_id = self.handling_tasks[worker.pid]

        try:
            task = self.scheduler_client.get_task(handling_task_id)

            if task.status is TaskStatus.DISPATCHED or task.status is TaskStatus.RUNNING:
                try:
                    self.scheduler_client.patch_task(task.id, TaskStatus.FAILED)
                    logger.warning("Set status to failed in the scheduler for task[id=%s]", handling_task_id)
                except HTTPError:
                    logger.exception("Could not patch scheduler task to failed")
        except HTTPError:
            logger.exception("Could not get scheduler task[id=%s]", handling_task_id)

    def _worker_args(self) -> tuple:
        return self.task_queue, self.item_handler, self.scheduler_client, self.handling_tasks

    def exit(self, signum: int | None = None) -> None:
        try:
            if signum:
                logger.info("Received %s, exiting", signal.Signals(signum).name)

            if not self.task_queue.empty():
                items: list[Task] = [self.task_queue.get() for _ in range(self.task_queue.qsize())]

                for p_item in items:
                    try:
                        self.scheduler_client.push_item(p_item)
                    except HTTPError:
                        logger.exception("Rescheduling task failed[id=%s]", p_item.id)

            killed_workers = []

            for worker in self.workers:  # Send all signals before joining, speeding up shutdowns
                try:
                    if worker.is_alive():
                        worker.kill()
                        killed_workers.append(worker)
                except ValueError:
                    pass  # worker is already closed

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


def _format_exit_code(exitcode: int | None) -> str:
    if exitcode is None or exitcode >= 0:
        return f"exitcode={exitcode}"

    return f"signal={signal.Signals(-exitcode).name}"


def _start_working(
    task_queue: multiprocessing.Queue,
    handler: Handler,
    scheduler_client: SchedulerClientInterface,
    handling_tasks: dict[int, str],
) -> None:
    logger.info("Started listening for tasks from worker[pid=%s]", os.getpid())

    while True:
        p_item = task_queue.get()
        status = TaskStatus.FAILED
        handling_tasks[os.getpid()] = str(p_item.id)

        try:
            scheduler_client.patch_task(p_item.id, TaskStatus.RUNNING)
            handler.handle(p_item.data)
            status = TaskStatus.COMPLETED
        except Exception:  # noqa
            logger.exception("An error occurred handling scheduler item[id=%s]", p_item.data.id)
        except:  # noqa
            logger.exception("An unhandled error occurred handling scheduler item[id=%s]", p_item.data.id)
            raise
        finally:
            try:
                if scheduler_client.get_task(p_item.id).status == TaskStatus.RUNNING:
                    # The docker runner could have handled this already
                    scheduler_client.patch_task(p_item.id, status)  # Note that implicitly, we have p_item.id == task_id
                    logger.info("Set status to %s in the scheduler for task[id=%s]", status, p_item.data.id)
            except HTTPError:
                logger.exception("Could not patch scheduler task to %s", status.value)


def get_runtime_manager(settings: Settings, queue: WorkerManager.Queue, log_level: str) -> WorkerManager:
    local_repository = get_local_repository()

    session = sessionmaker(bind=get_engine())()
    plugin_service = PluginService(create_plugin_storage(session), create_config_storage(session), local_repository)

    item_handler: Handler
    if queue is WorkerManager.Queue.BOEFJES:
        item_handler = BoefjeHandler(LocalBoefjeJobRunner(local_repository), plugin_service, bytes_api_client)
    else:
        item_handler = NormalizerHandler(
            LocalNormalizerJobRunner(local_repository), bytes_api_client, settings.scan_profile_whitelist
        )

    return SchedulerWorkerManager(item_handler, SchedulerAPIClient(str(settings.scheduler_api)), settings, log_level)
