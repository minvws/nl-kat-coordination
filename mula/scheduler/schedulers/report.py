from collections.abc import Callable
from concurrent import futures
from datetime import datetime, timezone
from typing import Any

import structlog
from opentelemetry import trace

from scheduler import context, queues, storage
from scheduler.models import Organisation, ReportTask, Task
from scheduler.storage import filters

from .scheduler import Scheduler

tracer = trace.get_tracer(__name__)


class ReportScheduler(Scheduler):
    ITEM_TYPE: Any = ReportTask

    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        organisation: Organisation,
        queue: queues.PriorityQueue | None = None,
        callback: Callable[..., None] | None = None,
    ):
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.organisation: Organisation = organisation
        self.create_schedule = False

        self.queue = queue or queues.PriorityQueue(
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
        )

    def run(self) -> None:
        # Rescheduling
        self.run_in_thread(
            name=f"scheduler-{self.scheduler_id}-reschedule",
            target=self.push_tasks_for_rescheduling,
            interval=60.0,
        )

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
                        filters.Filter(
                            column="scheduler_id",
                            operator="eq",
                            value=self.scheduler_id,
                        ),
                        filters.Filter(
                            column="deadline_at",
                            operator="lt",
                            value=datetime.now(timezone.utc),
                        ),
                        filters.Filter(
                            column="enabled",
                            operator="eq",
                            value=True,
                        ),
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
                report_task = ReportTask.parse_obj(schedule.data)
                executor.submit(
                    self.push_report_task,
                    report_task,
                    self.push_tasks_for_rescheduling.__name__,
                )

    def push_report_task(self, report_task: ReportTask, caller: str = "") -> None:
        self.logger.debug(
            "Pushing report task",
            task_hash=report_task.hash,
            organisation_id=self.organisation.id,
            scheduler_id=self.scheduler_id,
            caller=caller,
        )

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
            type=self.ITEM_TYPE,
            hash=report_task.hash,
            data=report_task,
        )

        try:
            self.push_item_to_queue_with_timeout(
                task,
                self.max_tries,
            )
        except queues.QueueFullError:
            self.logger.warning(
                "Could not add task to queue, queue was full: %s",
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
