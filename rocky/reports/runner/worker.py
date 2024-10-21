import multiprocessing as mp
import os
import signal
import sys
import time
from queue import Queue

import structlog
from django.conf import settings
from httpx import HTTPError
from pydantic import ValidationError

from reports.runner.models import ReportRunner, WorkerManager
from reports.runner.report_runner import LocalReportRunner
from rocky.bytes_client import get_bytes_client
from rocky.scheduler import SchedulerClient, Task, TaskStatus, scheduler_client

logger = structlog.get_logger(__name__)


class SchedulerWorkerManager(WorkerManager):
    def __init__(
        self,
        runner: ReportRunner,
        scheduler: SchedulerClient,
        pool_size: int,
        poll_interval: int,
        worker_heartbeat: int,
    ):
        self.runner = runner
        self.scheduler = scheduler
        self.pool_size = pool_size
        self.poll_interval = poll_interval
        self.worker_heartbeat = worker_heartbeat

        manager = mp.Manager()

        self.task_queue = manager.Queue()  # multiprocessing.Queue() will not work on macOS, see mp.Queue.qsize()
        self.handling_tasks = manager.dict()
        self.workers: list[mp.Process] = []

        self.exited = False

    def run(self) -> None:
        logger.info("Created worker pool for queue 'report'")

        self.workers = [mp.Process(target=_start_working, args=self._worker_args()) for _ in range(self.pool_size)]
        for worker in self.workers:
            worker.start()

        signal.signal(signal.SIGINT, lambda signum, _: self.exit(signum))
        signal.signal(signal.SIGTERM, lambda signum, _: self.exit(signum))

        while True:
            try:
                self._check_workers()
                self._fill_queue(self.task_queue)
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

    def _fill_queue(self, task_queue: Queue):
        if task_queue.qsize() > self.pool_size:
            time.sleep(self.worker_heartbeat)
            return

        try:
            queues = self.scheduler.get_queues()
        except HTTPError:
            # Scheduler is having issues, so make note of it and try again
            logger.exception("Getting the queues from the scheduler failed")
            time.sleep(self.poll_interval)  # But not immediately
            return

        # We do not target a specific queue since we start one runtime for all organisations
        # and queue ids contain the organisation_id
        queues = [q for q in queues if q.id.startswith("report")]

        logger.debug("Found queues: %s", [queue.id for queue in queues])

        all_queues_empty = True

        for queue in queues:
            logger.debug("Popping from queue %s", queue.id)

            try:
                p_item = self.scheduler.pop_item(queue.id)
            except (HTTPError, ValidationError):
                logger.error("Popping task from scheduler failed")
                time.sleep(self.poll_interval)
                continue

            if not p_item:
                logger.debug("Queue %s empty", queue.id)
                continue

            all_queues_empty = False

            logger.info("Handling task[%s]", p_item.id)

            try:
                task_queue.put(p_item)
                logger.info("Dispatched task[%s]", p_item.id)
            except:  # noqa
                logger.error("Exiting worker...")
                logger.info("Patching scheduler task[id=%s] to %s", p_item.id, TaskStatus.FAILED.value)

                try:
                    self.scheduler.patch_task(p_item.id, TaskStatus.FAILED)
                    logger.info("Set task status to %s in the scheduler for task[id=%s]", TaskStatus.FAILED, p_item.id)
                except HTTPError:
                    logger.error("Could not patch scheduler task to %s", TaskStatus.FAILED.value)

                raise

        if all_queues_empty:
            logger.debug("All queues empty, sleeping %f seconds", self.poll_interval)
            time.sleep(self.poll_interval)

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
            task = self.scheduler.get_task_details(handling_task_id)

            if task.status is TaskStatus.DISPATCHED or task.status is TaskStatus.RUNNING:
                try:
                    self.scheduler.patch_task(task.id, TaskStatus.FAILED)
                    logger.warning("Set status to failed in the scheduler for task[id=%s]", handling_task_id)
                except HTTPError:
                    logger.exception("Could not patch scheduler task to failed")
        except HTTPError:
            logger.exception("Could not get scheduler task[id=%s]", handling_task_id)

    def _worker_args(self) -> tuple:
        return self.task_queue, self.runner, self.scheduler, self.handling_tasks

    def exit(self, signum: int | None = None):
        try:
            if signum:
                logger.info("Received %s, exiting", signal.Signals(signum).name)

            if not self.task_queue.empty():
                tasks: list[Task] = [self.task_queue.get() for _ in range(self.task_queue.qsize())]

                for task in tasks:
                    try:
                        self.scheduler.push_task(task)
                    except HTTPError:
                        logger.exception("Rescheduling task failed[id=%s]", task.id)

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
    task_queue: mp.Queue, runner: ReportRunner, scheduler: SchedulerClient, handling_tasks: dict[int, str]
):
    logger.info("Started listening for tasks from worker[pid=%s]", os.getpid())

    while True:
        p_item = task_queue.get()
        status = TaskStatus.FAILED
        handling_tasks[os.getpid()] = str(p_item.id)

        try:
            scheduler.patch_task(p_item.id, TaskStatus.RUNNING)
            runner.run(p_item.data)
            status = TaskStatus.COMPLETED
        except Exception:  # noqa
            logger.exception("An error occurred handling scheduler item[id=%s]", p_item.id)
        except:  # noqa
            logger.exception("An unhandled error occurred handling scheduler item[id=%s]", p_item.id)
            raise
        finally:
            try:
                # The docker runner could have handled this already
                if scheduler.get_task_details(p_item.id).status == TaskStatus.RUNNING:
                    scheduler.patch_task(p_item.id, status)  # Note that implicitly, we have p_item.id == task_id
                    logger.info("Set status to %s in the scheduler for task[id=%s]", status, p_item.id)
            except HTTPError:
                logger.exception("Could not patch scheduler task to %s", status.value)


def get_runtime_manager() -> WorkerManager:
    return SchedulerWorkerManager(
        LocalReportRunner(get_bytes_client("")),  # These are set dynamically. Needs a refactor.
        scheduler_client(None),
        settings.POOL_SIZE,
        settings.POLL_INTERVAL,
        settings.WORKER_HEARTBEAT,
    )
