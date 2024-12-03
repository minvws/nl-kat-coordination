from collections.abc import Callable
from concurrent import futures
from datetime import datetime, timezone
from typing import Any

import structlog
from opentelemetry import trace

from scheduler import context, models, storage
from scheduler.schedulers import Scheduler
from scheduler.schedulers.queue import PriorityQueue, QueueFullError
from scheduler.storage import filters

tracer = trace.get_tracer(__name__)


class ReportScheduler(Scheduler):
    """Scheduler implementation for the creation of ReportTask models."""

    ID: str = "report"
    ITEM_TYPE: Any = models.ReportTask

    def __init__(self, ctx: context.AppContext):
        """Initializes the NormalizerScheduler.

        Args:
            ctx (context.AppContext): Application context of shared data (e.g.
                configuration, external services connections).
        """
        super().__init__(ctx=ctx, scheduler_id=self.ID, create_schedule=True)

    def run(self) -> None:
        """The run method is called when the schedulers is started. It will
        start the rescheduling process for the ReportTask models that are
        scheduled.
        """
        # Rescheduling
        self.run_in_thread(
            name=f"scheduler-{self.scheduler_id}-reschedule", target=self.push_tasks_for_rescheduling, interval=60.0
        )
        self.logger.info(
            "Report scheduler started", scheduler_id=self.scheduler_id, item_type=self.queue.item_type.__name__
        )

    @tracer.start_as_current_span(name="report_push_tasks_for_rescheduling")
    def push_tasks_for_rescheduling(self):
        if self.queue.full():
            self.logger.warning(
                "Report queue is full, not populating with new tasks",
                queue_qsize=self.queue.qsize(),
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
                exc_info=exc_db,
            )
            raise exc_db

        with futures.ThreadPoolExecutor(
            thread_name_prefix=f"ReportScheduler-TPE-{self.scheduler_id}-rescheduling"
        ) as executor:
            for schedule in schedules:
                report_task = models.ReportTask.model_validate(schedule.data)

                task = models.Task(
                    id=report_task.id,
                    scheduler_id=self.scheduler_id,
                    organisation=schedule.organisation,
                    type=self.ITEM_TYPE.type,
                    hash=report_task.hash,
                    data=report_task.model_dump(),
                )

                executor.submit(self.push_task, task, self.push_tasks_for_rescheduling.__name__)

    def push_task(self, task: models.Task, caller: str = "") -> None:
        if self.is_item_on_queue_by_hash(task.hash):
            self.logger.debug("Report task already on queue", scheduler_id=self.scheduler_id, caller=caller)
            return

        self.push_item_to_queue_with_timeout(task, self.max_tries)

        self.logger.info(
            "Report task pushed to queue",
            task_id=task.id,
            task_hash=task.hash,
            scheduler_id=self.scheduler_id,
            caller=caller,
        )
