import uuid
from collections.abc import Callable
from concurrent import futures
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import structlog
from opentelemetry import trace

from scheduler import context, queues, rankers, storage, utils
from scheduler.connectors import listeners
from scheduler.connectors.errors import ExternalServiceError
from scheduler.models import (
    OOI,
    Boefje,
    BoefjeTask,
    MutationOperationType,
    Organisation,
    Plugin,
    ScanProfileMutation,
    Task,
    TaskStatus,
)
from scheduler.storage import filters

from .scheduler import Scheduler

tracer = trace.get_tracer(__name__)


class BoefjeScheduler(Scheduler):
    """A KAT specific implementation of a Boefje scheduler. It extends
    the `Scheduler` class by adding an `organisation` attribute.

    Attributes:
        logger: A logger instance.
        organisation: The organisation that this scheduler is for.
    """

    ITEM_TYPE: Any = BoefjeTask

    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        organisation: Organisation,
        queue: queues.PriorityQueue | None = None,
        callback: Callable[..., None] | None = None,
    ):
        """Initializes the BoefjeScheduler.

        Args:
            ctx: The application context.
            scheduler_id: The id of the scheduler.
            organisation: The organisation that this scheduler is for.
            queue: The queue to use for this scheduler.
            callback: The callback function to call when a task is completed.
        """
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.organisation: Organisation = organisation

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
            create_schedule=True,
        )

        # Priority ranker
        self.priority_ranker = rankers.BoefjeRanker(self.ctx)

    def run(self) -> None:
        """The run method is called when the scheduler is started. It will
        start the listeners and the scheduling loops in separate threads. It
        is mainly tasked with populating the queue with tasks.

        - Scan profile mutations; when a scan profile is updated for an ooi
        e.g. the scan level is changed, we need to create new tasks for the
        ooi. We gather all boefjes that can run on the ooi and create tasks
        for them.

        - New boefjes; when new boefjes are added or enabled we find the ooi's
        that boefjes can run on, and create tasks for it.

        - Rescheduling; when a task has passed its deadline, we need to
        reschedule it.
        """
        # Scan profile mutations
        self.listeners["scan_profile_mutations"] = listeners.ScanProfileMutation(
            dsn=str(self.ctx.config.host_raw_data),
            queue=f"{self.organisation.id}__scan_profile_mutations",
            func=self.push_tasks_for_scan_profile_mutations,
            prefetch_count=self.ctx.config.rabbitmq_prefetch_count,
        )

        self.run_in_thread(
            name=f"BoefjeScheduler-{self.scheduler_id}-mutations",
            target=self.listeners["scan_profile_mutations"].listen,
            loop=False,
        )

        # New Boefjes
        self.run_in_thread(
            name=f"BoefjeScheduler-{self.scheduler_id}-new_boefjes",
            target=self.push_tasks_for_new_boefjes,
            interval=60.0,
        )

        # Rescheduling
        self.run_in_thread(
            name=f"scheduler-{self.scheduler_id}-reschedule",
            target=self.push_tasks_for_rescheduling,
            interval=60.0,
        )

        self.logger.info(
            "Boefje scheduler started for %s",
            self.organisation.id,
            organisation_id=self.organisation.id,
            scheduler_id=self.scheduler_id,
            item_type=self.queue.item_type.__name__,
        )

    @tracer.start_as_current_span("boefje_push_tasks_for_scan_profile_mutations")
    def push_tasks_for_scan_profile_mutations(self, body: bytes) -> None:
        """Create tasks for oois that have a scan level change.

        Args:
            mutation: The mutation that was received.
        """
        # Convert body into a ScanProfileMutation
        mutation = ScanProfileMutation.parse_raw(body)

        self.logger.debug(
            "Received scan level mutation %s for: %s",
            mutation.operation,
            mutation.primary_key,
            ooi_primary_key=mutation.primary_key,
            organisation_id=self.organisation.id,
            scheduler_id=self.scheduler_id,
        )

        # There should be an OOI in value
        ooi = mutation.value
        if ooi is None:
            self.logger.debug(
                "Mutation value is None, skipping",
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return

        if mutation.operation == MutationOperationType.DELETE:
            # When there are tasks of the ooi are on the queue, we need to
            # remove them from the queue.
            items, _ = self.ctx.datastores.pq_store.get_items(
                scheduler_id=self.scheduler_id,
                filters=filters.FilterRequest(
                    filters=[
                        filters.Filter(
                            column="data",
                            field="input_ooi",
                            operator="eq",
                            value=ooi.primary_key,
                        ),
                    ],
                ),
            )

            # Delete all items for this ooi, update all tasks for this ooi
            # to cancelled.
            for item in items:
                task = self.ctx.datastores.task_store.get_task(item.id)
                if task is None:
                    continue

                task.status = TaskStatus.CANCELLED
                self.ctx.datastores.task_store.update_task(task)

            return

        # What available boefjes do we have for this ooi?
        boefjes = self.get_boefjes_for_ooi(ooi)
        if not boefjes:
            self.logger.debug(
                "No boefjes available for %s",
                ooi.primary_key,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return

        with futures.ThreadPoolExecutor(
            thread_name_prefix=f"BoefjeScheduler-TPE-{self.scheduler_id}-mutations"
        ) as executor:
            for boefje in boefjes:
                if not self.has_boefje_permission_to_run(boefje, ooi):
                    self.logger.debug(
                        "Boefje not allowed to run on ooi",
                        boefje_id=boefje.id,
                        ooi_primary_key=ooi.primary_key,
                        organisation_id=self.organisation.id,
                        scheduler_id=self.scheduler_id,
                    )
                    continue

                boefje_task = BoefjeTask(
                    boefje=Boefje.parse_obj(boefje.dict()),
                    input_ooi=ooi.primary_key if ooi else None,
                    organization=self.organisation.id,
                )

                executor.submit(
                    self.push_boefje_task,
                    boefje_task,
                    self.push_tasks_for_scan_profile_mutations.__name__,
                )

    @tracer.start_as_current_span("boefje_push_tasks_for_new_boefjes")
    def push_tasks_for_new_boefjes(self) -> None:
        """When new boefjes are added or enabled we find the ooi's that
        boefjes can run on, and create tasks for it."""
        new_boefjes = None
        try:
            new_boefjes = self.ctx.services.katalogus.get_new_boefjes_by_org_id(self.organisation.id)
        except ExternalServiceError:
            self.logger.error(
                "Failed to get new boefjes for organisation: %s from katalogus",
                self.organisation.name,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return

        if new_boefjes is None or not new_boefjes:
            self.logger.debug(
                "No new boefjes for organisation: %s",
                self.organisation.name,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return

        self.logger.debug(
            "Received new boefjes",
            boefjes=[boefje.name for boefje in new_boefjes],
            organisation_id=self.organisation.id,
            scheduler_id=self.scheduler_id,
        )

        for boefje in new_boefjes:
            if not boefje.consumes:
                self.logger.debug(
                    "No consumes found for boefje: %s",
                    boefje.name,
                    boefje_id=boefje.id,
                    organisation_id=self.organisation.id,
                    scheduler_id=self.scheduler_id,
                )
                continue

            oois_by_object_type: list[OOI] = []
            try:
                oois_by_object_type = self.ctx.services.octopoes.get_objects_by_object_types(
                    self.organisation.id,
                    boefje.consumes,
                    list(range(boefje.scan_level, 5)),
                )
            except ExternalServiceError as exc:
                self.logger.error(
                    "Could not get oois for organisation: %s from octopoes",
                    self.organisation.name,
                    organisation_id=self.organisation.id,
                    scheduler_id=self.scheduler_id,
                    exc_info=exc,
                )
                continue

            with futures.ThreadPoolExecutor(
                thread_name_prefix=f"BoefjeScheduler-TPE-{self.scheduler_id}-new_boefjes"
            ) as executor:
                for ooi in oois_by_object_type:
                    if not self.has_boefje_permission_to_run(boefje, ooi):
                        self.logger.debug(
                            "Boefje not allowed to run on ooi",
                            boefje_id=boefje.id,
                            ooi_primary_key=ooi.primary_key,
                            organisation_id=self.organisation.id,
                            scheduler_id=self.scheduler_id,
                        )
                        continue

                    boefje_task = BoefjeTask(
                        boefje=Boefje.parse_obj(boefje.dict()),
                        input_ooi=ooi.primary_key,
                        organization=self.organisation.id,
                    )

                    executor.submit(
                        self.push_boefje_task,
                        boefje_task,
                        self.push_tasks_for_new_boefjes.__name__,
                    )

    @tracer.start_as_current_span("boefje_push_tasks_for_rescheduling")
    def push_tasks_for_rescheduling(self):
        if self.queue.full():
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks",
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

        if not schedules:
            self.logger.debug(
                "No schedules tasks found for scheduler: %s",
                self.scheduler_id,
                scheduler_id=self.scheduler_id,
                organisation_id=self.organisation.id,
            )
            return

        with futures.ThreadPoolExecutor(
            thread_name_prefix=f"BoefjeScheduler-TPE-{self.scheduler_id}-rescheduling"
        ) as executor:
            for schedule in schedules:
                boefje_task = BoefjeTask.parse_obj(schedule.data)

                # Plugin still exists?
                try:
                    plugin = self.ctx.services.katalogus.get_plugin_by_id_and_org_id(
                        boefje_task.boefje.id,
                        self.organisation.id,
                    )
                    if not plugin:
                        self.logger.info(
                            "Boefje does not exist anymore, skipping and disabling schedule",
                            boefje_id=boefje_task.boefje.id,
                            schedule_id=schedule.id,
                            organisation_id=self.organisation.id,
                            scheduler_id=self.scheduler_id,
                        )
                        schedule.enabled = False
                        self.ctx.datastores.schedule_store.update_schedule(schedule)
                        continue
                except ExternalServiceError as exc_plugin:
                    self.logger.error(
                        "Could not get plugin %s from katalogus",
                        boefje_task.boefje.id,
                        boefje_id=boefje_task.boefje.id,
                        schedule_id=schedule.id,
                        organisation_id=self.organisation.id,
                        scheduler_id=self.scheduler_id,
                        exc_info=exc_plugin,
                    )
                    continue

                # Plugin still enabled?
                if not plugin.enabled:
                    self.logger.debug(
                        "Boefje is disabled, skipping",
                        boefje_id=boefje_task.boefje.id,
                        schedule_id=schedule.id,
                        organisation_id=self.organisation.id,
                        scheduler_id=self.scheduler_id,
                    )
                    schedule.enabled = False
                    self.ctx.datastores.schedule_store.update_schedule(schedule)
                    continue

                # Plugin a boefje?
                if plugin.type != "boefje":
                    # We don't disable the schedule, since we should've gotten
                    # schedules for boefjes only.
                    self.logger.warning(
                        "Plugin is not a boefje, skipping",
                        plugin_id=plugin.id,
                        schedule_id=schedule.id,
                        organisation_id=self.organisation.id,
                        scheduler_id=self.scheduler_id,
                    )
                    continue

                # When the boefje task has an ooi, we need to do some additional
                # checks.
                ooi = None
                if boefje_task.input_ooi:
                    # OOI still exists?
                    try:
                        ooi = self.ctx.services.octopoes.get_object(boefje_task.organization, boefje_task.input_ooi)
                        if not ooi:
                            self.logger.info(
                                "OOI does not exist anymore, skipping and disabling schedule",
                                ooi_primary_key=boefje_task.input_ooi,
                                schedule_id=schedule.id,
                                organisation_id=self.organisation.id,
                                scheduler_id=self.scheduler_id,
                            )
                            schedule.enabled = False
                            self.ctx.datastores.schedule_store.update_schedule(schedule)
                            continue
                    except ExternalServiceError as exc_ooi:
                        self.logger.error(
                            "Could not get ooi %s from octopoes",
                            boefje_task.input_ooi,
                            ooi_primary_key=boefje_task.input_ooi,
                            schedule_id=schedule.id,
                            organisation_id=self.organisation.id,
                            scheduler_id=self.scheduler_id,
                            exc_info=exc_ooi,
                        )
                        continue

                    # Boefje still consuming ooi type?
                    if ooi.object_type not in plugin.consumes:
                        self.logger.debug(
                            "Boefje does not consume ooi anymore, skipping",
                            boefje_id=boefje_task.boefje.id,
                            ooi_primary_key=ooi.primary_key,
                            organisation_id=self.organisation.id,
                            scheduler_id=self.scheduler_id,
                        )
                        schedule.enabled = False
                        self.ctx.datastores.schedule_store.update_schedule(schedule)
                        continue

                    # TODO: do we want to disable the schedule when a
                    # boefje is not allowed to scan an ooi?

                    # Boefje allowed to scan ooi?
                    if not self.has_boefje_permission_to_run(plugin, ooi):
                        self.logger.info(
                            "Boefje not allowed to scan ooi, skipping and disabling schedule",
                            boefje_id=boefje_task.boefje.id,
                            ooi_primary_key=ooi.primary_key,
                            schedule_id=schedule.id,
                            organisation_id=self.organisation.id,
                            scheduler_id=self.scheduler_id,
                        )
                        schedule.enabled = False
                        self.ctx.datastores.schedule_store.update_schedule(schedule)
                        continue

                new_boefje_task = BoefjeTask(
                    boefje=Boefje.parse_obj(plugin.dict()),
                    input_ooi=ooi.primary_key if ooi else None,
                    organization=self.organisation.id,
                )

                executor.submit(
                    self.push_boefje_task,
                    new_boefje_task,
                    self.push_tasks_for_rescheduling.__name__,
                )

    @tracer.start_as_current_span("boefje_push_task")
    def push_boefje_task(
        self,
        boefje_task: BoefjeTask,
        caller: str = "",
    ) -> None:
        """Given a Boefje and OOI create a BoefjeTask and push it onto
        the queue.

        Args:
            boefje: Boefje to run.
            ooi: OOI to run Boefje on.
            caller: The name of the function that called this function, used for logging.

        """
        self.logger.debug(
            "Pushing boefje task",
            task_hash=boefje_task.hash,
            boefje_id=boefje_task.boefje.id,
            ooi_primary_key=boefje_task.input_ooi,
            organisation_id=self.organisation.id,
            scheduler_id=self.scheduler_id,
            caller=caller,
        )

        try:
            grace_period_passed = self.has_boefje_task_grace_period_passed(boefje_task)
            if not grace_period_passed:
                self.logger.debug(
                    "Task has not passed grace period: %s",
                    boefje_task.hash,
                    task_hash=boefje_task.hash,
                    organisation_id=self.organisation.id,
                    scheduler_id=self.scheduler_id,
                    caller=caller,
                )
                return
        except Exception as exc_grace_period:
            self.logger.warning(
                "Could not check if grace period has passed: %s",
                boefje_task.hash,
                task_hash=boefje_task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
                exc_info=exc_grace_period,
            )
            return

        try:
            is_stalled = self.has_boefje_task_stalled(boefje_task)
            if is_stalled:
                self.logger.debug(
                    "Task is stalled: %s",
                    boefje_task.hash,
                    task_hash=boefje_task.hash,
                    organisation_id=self.organisation.id,
                    scheduler_id=self.scheduler_id,
                    caller=caller,
                )

                # Update task in datastore to be failed
                task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(boefje_task.hash)
                task_db.status = TaskStatus.FAILED
                self.ctx.datastores.task_store.update_task(task_db)
        except Exception as exc_stalled:
            self.logger.warning(
                "Could not check if task is stalled: %s",
                boefje_task.hash,
                boefje_task_hash=boefje_task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
                exc_info=exc_stalled,
            )
            return

        try:
            is_running = self.has_boefje_task_started_running(boefje_task)
            if is_running:
                self.logger.debug(
                    "Task is still running: %s",
                    boefje_task.hash,
                    task_hash=boefje_task.hash,
                    organisation_id=self.organisation.id,
                    scheduler_id=self.scheduler_id,
                    caller=caller,
                )
                return
        except Exception as exc_running:
            self.logger.warning(
                "Could not check if task is running: %s",
                boefje_task.hash,
                task_hash=boefje_task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
                exc_info=exc_running,
            )
            return

        if self.is_item_on_queue_by_hash(boefje_task.hash):
            self.logger.debug(
                "Task is already on queue: %s",
                boefje_task.hash,
                task_hash=boefje_task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
                exc_info=True,
            )
            return

        prior_tasks = self.ctx.datastores.task_store.get_tasks_by_hash(boefje_task.hash)
        score = self.priority_ranker.rank(
            SimpleNamespace(
                prior_tasks=prior_tasks,
                task=boefje_task,
            )
        )

        task = Task(
            id=boefje_task.id,
            scheduler_id=self.scheduler_id,
            type=self.ITEM_TYPE.type,
            priority=score,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
        )

        try:
            self.push_item_to_queue_with_timeout(
                task,
                self.max_tries,
            )
        except queues.QueueFullError:
            self.logger.warning(
                "Could not add task to queue, queue was full: %s",
                boefje_task.hash,
                task_hash=boefje_task.hash,
                queue_qsize=self.queue.qsize(),
                queue_maxsize=self.queue.maxsize,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )
            return

        self.logger.info(
            "Created boefje task",
            task_id=task.id,
            task_hash=task.hash,
            boefje_id=boefje_task.boefje.id,
            ooi_primary_key=boefje_task.input_ooi,
            organisation_id=self.organisation.id,
            scheduler_id=self.scheduler_id,
            caller=caller,
        )

    def push_item_to_queue(self, item: Task) -> Task:
        """Some boefje scheduler specific logic before pushing the item to the
        queue."""
        boefje_task = BoefjeTask.parse_obj(item.data)

        # Check if id's are unique and correctly set. Same id's are necessary
        # for the task runner.
        if item.id != boefje_task.id or self.ctx.datastores.task_store.get_task(item.id):
            new_id = uuid.uuid4()
            boefje_task.id = new_id
            item.id = new_id
            item.data = boefje_task.model_dump()

        return super().push_item_to_queue(item)

    @tracer.start_as_current_span("boefje_has_boefje_permission_to_run")
    def has_boefje_permission_to_run(
        self,
        boefje: Plugin,
        ooi: OOI,
    ) -> bool:
        """Checks whether a boefje is allowed to run on an ooi.

        Args:
            boefje: The boefje to check.
            ooi: The ooi to check.

        Returns:
            True if the boefje is allowed to run on the ooi, False otherwise.
        """
        if boefje.enabled is False:
            self.logger.debug(
                "Boefje: %s is disabled",
                boefje.name,
                boefje_id=boefje.id,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return False

        boefje_scan_level = boefje.scan_level
        if boefje_scan_level is None:
            self.logger.warning(
                "No scan level found for boefje: %s",
                boefje.id,
                boefje_id=boefje.id,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return False

        # We allow boefjes without an ooi to run.
        if ooi is None:
            return True

        if ooi.scan_profile is None:
            self.logger.debug(
                "No scan_profile found for ooi: %s",
                ooi.primary_key,
                ooi_primary_key=ooi.primary_key,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return False

        ooi_scan_level = ooi.scan_profile.level
        if ooi_scan_level is None:
            self.logger.warning(
                "No scan level found for ooi: %s",
                ooi.primary_key,
                ooi_primary_key=ooi.primary_key,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return False

        # Boefje intensity score ooi clearance level, range
        # from 0 to 4. 4 being the highest intensity, and 0 being
        # the lowest. OOI clearance level defines what boefje
        # intensity is allowed to run on.
        if boefje_scan_level > ooi_scan_level:
            self.logger.debug(
                "Boefje: %s scan level %s is too intense for ooi: %s scan level %s",
                boefje.id,
                boefje_scan_level,
                ooi.primary_key,
                ooi_scan_level,
                boefje_id=boefje.id,
                ooi_primary_key=ooi.primary_key,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return False

        return True

    @tracer.start_as_current_span("boefje_has_boefje_task_started_running")
    def has_boefje_task_started_running(self, task: BoefjeTask) -> bool:
        """Check if the same task is already running.

        Args:
            task: The BoefjeTask to check.

        Returns:
            True if the task is still running, False otherwise.
        """
        # Is task still running according to the datastore?
        task_db = None
        try:
            task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(task.hash)
        except Exception as exc_db:
            self.logger.error(
                "Could not get latest task by hash: %s",
                task.hash,
                task_id=task.id,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                exc_info=exc_db,
            )
            raise exc_db

        if task_db is not None and task_db.status not in [
            TaskStatus.FAILED,
            TaskStatus.COMPLETED,
        ]:
            self.logger.debug(
                "Task is still running, according to the datastore",
                task_id=task_db.id,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return True

        # Is task running according to bytes?
        try:
            task_bytes = self.ctx.services.bytes.get_last_run_boefje(
                boefje_id=task.boefje.id,
                input_ooi=task.input_ooi,
                organization_id=task.organization,
            )
        except ExternalServiceError as exc:
            self.logger.error(
                "Failed to get last run boefje from bytes",
                boefje_id=task.boefje.id,
                input_ooi_primary_key=task.input_ooi,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                exc_info=exc,
            )
            raise exc

        # Task has been finished (failed, or succeeded) according to
        # the datastore, but we have no results of it in bytes, meaning
        # we have a problem. However when the grace period has been reached we
        # should not raise an error.
        if (
            task_bytes is None
            and task_db is not None
            and task_db.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            and (
                task_db.modified_at is not None
                and task_db.modified_at
                > datetime.now(timezone.utc) - timedelta(seconds=self.ctx.config.pq_grace_period)
            )
        ):
            self.logger.error(
                "Task has been finished, but no results found in bytes, "
                "please review the bytes logs for more information regarding "
                "this error.",
                task_id=task_db.id,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            raise RuntimeError("Task has been finished, but no results found in bytes")

        if task_bytes is not None and task_bytes.ended_at is None and task_bytes.started_at is not None:
            self.logger.debug(
                "Task is still running, according to bytes",
                task_id=task_bytes.id,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return True

        return False

    @tracer.start_as_current_span("boefje_is_task_stalled")
    def has_boefje_task_stalled(self, task: BoefjeTask) -> bool:
        """Check if the same task is stalled.

        Args:
            task: The BoefjeTask to check.

        Returns:
            True if the task is stalled, False otherwise.
        """
        task_db = None
        try:
            task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(task.hash)
        except Exception as exc_db:
            self.logger.warning(
                "Could not get latest task by hash: %s",
                task.hash,
                task_hash=task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                exc_info=exc_db,
            )
            raise exc_db

        if (
            task_db is not None
            and task_db.status == TaskStatus.DISPATCHED
            and (
                task_db.modified_at is not None
                and datetime.now(timezone.utc)
                > task_db.modified_at + timedelta(seconds=self.ctx.config.pq_grace_period)
            )
        ):
            return True

        return False

    @tracer.start_as_current_span("boefje_has_boefje_task_grace_period_passed")
    def has_boefje_task_grace_period_passed(self, task: BoefjeTask) -> bool:
        """Check if the grace period has passed for a task in both the
        datastore and bytes.

        NOTE: We don't check the status of the task since this needs to be done
        by checking if the task is still running or not.

        Args:
            task: Task to check.

        Returns:
            True if the grace period has passed, False otherwise.
        """
        try:
            task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(task.hash)
        except Exception as exc_db:
            self.logger.warning(
                "Could not get latest task by hash: %s",
                task.hash,
                task_hash=task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                exc_info=exc_db,
            )
            raise exc_db

        # Has grace period passed according to datastore?
        if task_db is not None and datetime.now(timezone.utc) - task_db.modified_at < timedelta(
            seconds=self.ctx.config.pq_grace_period
        ):
            self.logger.debug(
                "Task has not passed grace period, according to the datastore",
                task_id=task_db.id,
                task_hash=task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return False

        try:
            task_bytes = self.ctx.services.bytes.get_last_run_boefje(
                boefje_id=task.boefje.id,
                input_ooi=task.input_ooi,
                organization_id=task.organization,
            )
        except ExternalServiceError as exc_bytes:
            self.logger.error(
                "Failed to get last run boefje from bytes",
                boefje_id=task.boefje.id,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
                exc_info=exc_bytes,
            )
            raise exc_bytes

        # Did the grace period pass, according to bytes?
        if (
            task_bytes is not None
            and task_bytes.ended_at is not None
            and datetime.now(timezone.utc) - task_bytes.ended_at < timedelta(seconds=self.ctx.config.pq_grace_period)
        ):
            self.logger.debug(
                "Task has not passed grace period, according to bytes",
                task_id=task_bytes.id,
                task_hash=task.hash,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return False

        return True

    def get_boefjes_for_ooi(self, ooi) -> list[Plugin]:
        """Get available all boefjes (enabled and disabled) for an ooi.

        Args:
            ooi: The models.OOI to get boefjes for.

        Returns:
            A list of Plugin of type Boefje that can be run on the ooi.
        """
        try:
            boefjes = self.ctx.services.katalogus.get_boefjes_by_type_and_org_id(
                ooi.object_type,
                self.organisation.id,
            )
        except ExternalServiceError:
            self.logger.error(
                "Could not get boefjes for object_type: %s",
                ooi.object_type,
                object_type=ooi.object_type,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return []

        if boefjes is None:
            self.logger.debug(
                "No boefjes found for type: %s",
                ooi.object_type,
                input_ooi_primary_key=ooi.primary_key,
                organisation_id=self.organisation.id,
                scheduler_id=self.scheduler_id,
            )
            return []

        self.logger.debug(
            "Found %s boefjes for ooi: %s",
            len(boefjes),
            ooi,
            input_ooi_primary_key=ooi.primary_key,
            boefjes=[boefje.id for boefje in boefjes],
            organisation_id=self.organisation.id,
            scheduler_id=self.scheduler_id,
        )

        return boefjes

    def calculate_deadline(self, task: Task) -> datetime:
        """Calculate the deadline for a task.

        Args:
            task: The task to calculate the deadline for.

        Returns:
            The calculated deadline.
        """
        # Does the boefje have an interval defined?
        interval = utils.deep_get(task.data, ["boefje", "interval"])
        if interval is not None:
            return datetime.now(timezone.utc) + timedelta(seconds=interval)  # FIXME: check if it is seconds or minutes

        return super().calculate_deadline(task)
