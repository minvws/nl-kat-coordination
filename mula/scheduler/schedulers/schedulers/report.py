from collections.abc import Callable
from concurrent import futures
from datetime import datetime, timezone
from typing import Any

import structlog
from opentelemetry import trace

from scheduler import context, storage
from scheduler.models import Organisation, ReportTask, Task, TaskStatus
from scheduler.schedulers import Scheduler
from scheduler.schedulers.queue import PriorityQueue, QueueFullError
from scheduler.storage import filters

tracer = trace.get_tracer(__name__)


class ReportScheduler(Scheduler):
    ITEM_TYPE: Any = ReportTask

    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        organisation: Organisation,
        queue: PriorityQueue | None = None,
        callback: Callable[..., None] | None = None,
    ):
        self.logger: structlog.BoundLogger = structlog.get_logger(__name__)
        self.organisation = organisation
        self.queue = queue or PriorityQueue(
            pq_id=scheduler_id,
            maxsize=ctx.config.pq_maxsize,
            item_type=self.ITEM_TYPE,
            allow_priority_updates=True,
            pq_store=ctx.datastores.pq_store,
        )

        super().__init__(
            ctx=ctx,
            queue=self.queue,
            scheduler_id=scheduler_id,
            callback=callback,
            create_schedule=True,
            auto_calculate_deadline=False,
        )

    def run(self) -> None:
        # Rescheduling
        self.run_in_thread(
            name=f"scheduler-{self.scheduler_id}-reschedule", target=self.push_tasks_for_rescheduling, interval=60.0
        )

    @tracer.start_as_current_span(name="report_push_tasks_for_rescheduling")
    def push_tasks_for_rescheduling(self):
        if self.queue.full():
            self.logger.warning(
                "Report queue is full, not populating with new tasks",
                queue_qsize=self.queue.qsize(),
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return

        try:
            schedules, _ = self.ctx.datastores.schedule_store.get_schedules(
                filters=filters.FilterRequest(
                    filters=[
                        filters.Filter(column="scheduler_id", operator="eq", value=self.scheduler_id),
                        filters.Filter(column="deadline_at", operator="lt", value=datetime.now(timezone.utc)),
                        filters.Filter(column="enabled", operator="eq", value=True),
                    ]
                )
            )
        except storage.errors.StorageError as exc_db:
            self.logger.error(
                "Could not get schedules for rescheduling %s",
                self.scheduler_id,
                scheduler_id=self.scheduler_id,
                organisation_id=self.organisation.id,
                exc_info=exc_db,
            )
            raise exc_db

        with futures.ThreadPoolExecutor(
            thread_name_prefix=f"ReportScheduler-TPE-{self.scheduler_id}-rescheduling"
        ) as executor:
            for schedule in schedules:
                report_task = ReportTask.model_validate(schedule.data)
                executor.submit(self.push_report_task, report_task, self.push_tasks_for_rescheduling.__name__)

    def push_report_task(self, report_task: ReportTask, caller: str = "") -> None:
        self.logger.debug(
            "Pushing report task",
            task_hash=report_task.hash,
            organisation_id=self.organisation.id,
            scheduler_id=self.scheduler_id,
            caller=caller,
        )

        if self.has_report_task_started_running(report_task):
            self.logger.debug(
                "Report task already running",
                task_hash=report_task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )
            return

        if self.is_item_on_queue_by_hash(report_task.hash):
            self.logger.debug(
                "Report task already on queue",
                task_hash=report_task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )
            return

        task = Task(
            scheduler_id=self.scheduler_id,
            priority=int(datetime.now().timestamp()),
            type=self.ITEM_TYPE.type,
            hash=report_task.hash,
            data=report_task.model_dump(),
        )

        try:
            self.push_item_to_queue_with_timeout(task, self.max_tries)
        except QueueFullError:
            self.logger.warning(
                "Could not add task %s to queue, queue was full",
                report_task.hash,
                task_hash=report_task.hash,
                queue_qsize=self.queue.qsize(),
                queue_maxsize=self.queue.maxsize,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )
            return

        self.logger.info(
            "Report task pushed to queue",
            task_id=task.id,
            task_hash=report_task.hash,
            organisation_id=self.organisation.id,
            scheduler_id=self.scheduler_id,
            caller=caller,
        )

    def has_report_task_started_running(self, task: ReportTask) -> bool:
        task_db = None
        try:
            task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(task.hash)
        except storage.errors.StorageError as exc_db:
            self.logger.error(
                "Could not get latest task by hash %s",
                task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                exc_info=exc_db,
            )
            raise exc_db

        if task_db is not None and task_db.status not in [TaskStatus.FAILED, TaskStatus.COMPLETED]:
            self.logger.debug(
                "Task is still running, according to the datastore",
                task_id=task_db.id,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return True

        return False
