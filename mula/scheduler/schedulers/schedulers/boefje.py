import uuid
from concurrent import futures
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from opentelemetry import trace
from pydantic import ValidationError

from scheduler import clients, context, models, utils
from scheduler.clients.errors import ExternalServiceError
from scheduler.models import MutationOperationType
from scheduler.models.ooi import RunOn
from scheduler.schedulers import Scheduler, rankers
from scheduler.schedulers.errors import exception_handler
from scheduler.storage import filters
from scheduler.storage.errors import StorageError

tracer = trace.get_tracer(__name__)


class BoefjeScheduler(Scheduler):
    """Scheduler implementation for the creation of BoefjeTask models.

    Attributes:
        ranker: The ranker to calculate the priority of a task.
    """

    ID: Literal["boefje"] = "boefje"
    TYPE: models.SchedulerType = models.SchedulerType.BOEFJE
    ITEM_TYPE: Any = models.BoefjeTask

    def __init__(self, ctx: context.AppContext):
        """Initializes the BoefjeScheduler.

        Args:
            ctx (context.AppContext): Application context of shared data (e.g.
                configuration, external services connections).
        """
        super().__init__(ctx=ctx, scheduler_id=self.ID, create_schedule=True, auto_calculate_deadline=True)
        self.ranker = rankers.BoefjeRankerTimeBased(self.ctx)

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
        self.listeners["mutations"] = clients.ScanProfileMutation(
            dsn=str(self.ctx.config.host_raw_data),
            queue="scan_profile_mutations",
            func=self.process_mutations,
            prefetch_count=self.ctx.config.rabbitmq_prefetch_count,
        )

        self.run_in_thread(name="BoefjeScheduler-mutations", target=self.listeners["mutations"].listen, loop=False)
        self.run_in_thread(name="BoefjeScheduler-new_boefjes", target=self.process_new_boefjes, interval=60.0)
        self.run_in_thread(name="BoefjeScheduler-rescheduling", target=self.process_rescheduling, interval=60.0)

        self.logger.info(
            "Boefje scheduler started", scheduler_id=self.scheduler_id, item_type=self.queue.item_type.__name__
        )

    @tracer.start_as_current_span("BoefjeScheduler.process_mutations")
    def process_mutations(self, body: bytes) -> None:
        """Create tasks for oois that have a scan level change.

        Args:
            mutation: The mutation that was received.
        """
        try:
            # Convert body into a ScanProfileMutation
            mutation = models.ScanProfileMutation.model_validate_json(body)
            self.logger.debug(
                "Received scan level mutation %s for: %s",
                mutation.operation,
                mutation.primary_key,
                ooi_primary_key=mutation.primary_key,
                scheduler_id=self.scheduler_id,
            )

            # There should be an OOI in value
            ooi = mutation.value
            if ooi is None:
                self.logger.debug("Mutation value is None, skipping", scheduler_id=self.scheduler_id)
                return

            # When the mutation is a delete operation, we need to remove all tasks
            if mutation.operation == models.MutationOperationType.DELETE:
                items, _ = self.ctx.datastores.pq_store.get_items(
                    scheduler_id=self.scheduler_id,
                    filters=filters.FilterRequest(
                        filters=[filters.Filter(column="data", field="input_ooi", operator="eq", value=ooi.primary_key)]
                    ),
                )

                # Delete all items for this ooi, update all tasks for this ooi
                # to cancelled.
                for item in items:
                    task = self.ctx.datastores.task_store.get_task(item.id)
                    if task is None:
                        continue

                    task.status = models.TaskStatus.CANCELLED
                    self.ctx.datastores.task_store.update_task(task)

                return

            # What available boefjes do we have for this ooi?
            boefjes = self.get_boefjes_for_ooi(ooi, mutation.client_id)
            if not boefjes:
                self.logger.debug("No boefjes available for %s", ooi.primary_key, scheduler_id=self.scheduler_id)
                return
        except (StorageError, ValidationError):
            self.logger.exception("Error occurred while processing mutation", scheduler_id=self.scheduler_id)
            return

        # Create tasks for the boefjes
        boefje_tasks = []
        for boefje in boefjes:
            if not self.has_boefje_permission_to_run(boefje, ooi):
                self.logger.debug(
                    "Boefje not allowed to run on ooi",
                    boefje_id=boefje.id,
                    ooi_primary_key=ooi.primary_key,
                    scheduler_id=self.scheduler_id,
                )
                continue

            create_schedule, run_task = True, True

            # What type of run boefje is it?
            if boefje.run_on:
                create_schedule = False
                run_task = False
                if mutation.operation == MutationOperationType.CREATE:
                    run_task = RunOn.CREATE in boefje.run_on
                elif mutation.operation == MutationOperationType.UPDATE:
                    run_task = RunOn.UPDATE in boefje.run_on

            if not run_task:
                self.logger.debug(
                    "Based on boefje run on type, skipping",
                    boefje_id=boefje.id,
                    ooi_primary_key=ooi.primary_key,
                    organisation_id=mutation.client_id,
                    scheduler_id=self.scheduler_id,
                )
                continue

            boefje_tasks.append(
                models.BoefjeTask(
                    boefje=models.Boefje.model_validate(boefje.model_dump()),
                    input_ooi=ooi.primary_key if ooi else None,
                    organization=mutation.client_id,
                )
            )

        with futures.ThreadPoolExecutor(thread_name_prefix=f"TPE-{self.scheduler_id}-mutations") as executor:
            for boefje_task in boefje_tasks:
                executor.submit(
                    self.push_boefje_task,
                    boefje_task,
                    mutation.client_id,
                    create_schedule,
                    self.process_mutations.__name__,
                )

    @tracer.start_as_current_span("BoefjeScheduler.process_new_boefjes")
    def process_new_boefjes(self) -> None:
        """When new boefjes are added or enabled we find the ooi's that
        boefjes can run on, and create tasks for it."""
        boefje_tasks = []

        # TODO: this should be optimized see #3357
        try:
            orgs = self.ctx.services.katalogus.get_organisations()
        except ExternalServiceError:
            self.logger.exception("Error occurred while processing new boefjes", scheduler_id=self.scheduler_id)
            return

        for org in orgs:
            try:
                # Get new boefjes for organisation
                new_boefjes = self.ctx.services.katalogus.get_new_boefjes_by_org_id(org.id)
                if not new_boefjes:
                    self.logger.debug("No new boefjes found for organisation", organisation_id=org.id)
                    continue

                # Get all oois for the new boefjes
                for boefje in new_boefjes:
                    oois = self.get_oois_for_boefje(boefje, org.id)
                    for ooi in oois:
                        boefje_task = models.BoefjeTask(
                            boefje=models.Boefje.model_validate(boefje.dict()),
                            input_ooi=ooi.primary_key,
                            organization=org.id,
                        )

                        boefje_tasks.append((boefje_task, org.id))
            except ExternalServiceError:
                self.logger.warning(
                    "Error occurred while processing new boefjes",
                    organisation_id=org.id,
                    scheduler_id=self.scheduler_id,
                )
                continue

        with futures.ThreadPoolExecutor(thread_name_prefix=f"TPE-{self.scheduler_id}-new_boefjes") as executor:
            for boefje_task, org_id in boefje_tasks:
                executor.submit(
                    self.push_boefje_task, boefje_task, org_id, self.create_schedule, self.process_new_boefjes.__name__
                )

    @tracer.start_as_current_span("BoefjeScheduler.process_rescheduling")
    def process_rescheduling(self):
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
            if not schedules:
                self.logger.debug(
                    "No schedules tasks found for scheduler: %s", self.scheduler_id, scheduler_id=self.scheduler_id
                )
                return
        except StorageError:
            self.logger.exception("Error occurred while processing rescheduling", scheduler_id=self.scheduler_id)
            return

        with futures.ThreadPoolExecutor(thread_name_prefix=f"TPE-{self.scheduler_id}-rescheduling") as executor:
            for schedule in schedules:
                try:
                    boefje_task = models.BoefjeTask.model_validate(schedule.data)

                    # Plugin still exists?
                    plugin = self.ctx.services.katalogus.get_plugin_by_id_and_org_id(
                        boefje_task.boefje.id, schedule.organisation
                    )
                    if not plugin:
                        self.logger.info(
                            "Boefje does not exist anymore, skipping and disabling schedule",
                            boefje_id=boefje_task.boefje.id,
                            schedule_id=schedule.id,
                            scheduler_id=self.scheduler_id,
                        )
                        schedule.enabled = False
                        self.ctx.datastores.schedule_store.update_schedule(schedule)
                        continue

                    # Plugin still enabled?
                    if not plugin.enabled:
                        self.logger.debug(
                            "Boefje is disabled, skipping",
                            boefje_id=boefje_task.boefje.id,
                            schedule_id=schedule.id,
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
                            organisation_id=schedule.organisation,
                            scheduler_id=self.scheduler_id,
                        )
                        continue

                    # When the boefje task has an ooi, we need to do some additional
                    # checks.
                    ooi = None
                    if boefje_task.input_ooi:
                        # OOI still exists?
                        ooi = self.ctx.services.octopoes.get_object(boefje_task.organization, boefje_task.input_ooi)
                        if not ooi:
                            self.logger.info(
                                "OOI does not exist anymore, skipping and disabling schedule",
                                ooi_primary_key=boefje_task.input_ooi,
                                schedule_id=schedule.id,
                                organisation_id=schedule.organisation,
                                scheduler_id=self.scheduler_id,
                            )
                            schedule.enabled = False
                            self.ctx.datastores.schedule_store.update_schedule(schedule)
                            continue

                        # Boefje still consuming ooi type?
                        if ooi.object_type not in plugin.consumes:
                            self.logger.debug(
                                "Boefje does not consume ooi anymore, skipping",
                                boefje_id=boefje_task.boefje.id,
                                ooi_primary_key=ooi.primary_key,
                                organisation_id=schedule.organisation,
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
                                organisation_id=schedule.organisation,
                                scheduler_id=self.scheduler_id,
                            )
                            schedule.enabled = False
                            self.ctx.datastores.schedule_store.update_schedule(schedule)
                            continue

                    new_boefje_task = models.BoefjeTask(
                        boefje=models.Boefje.model_validate(plugin.dict()),
                        input_ooi=ooi.primary_key if ooi else None,
                        organization=schedule.organisation,
                    )
                except (StorageError, ValidationError, ExternalServiceError):
                    self.logger.exception(
                        "Error occurred while processing rescheduling",
                        schedule_id=schedule.id,
                        scheduler_id=self.scheduler_id,
                    )
                    continue

                executor.submit(
                    self.push_boefje_task,
                    new_boefje_task,
                    schedule.organisation,
                    self.create_schedule,
                    self.process_rescheduling.__name__,
                )

    @exception_handler
    @tracer.start_as_current_span("BoefjeScheduler.push_boefje_task")
    def push_boefje_task(
        self, boefje_task: models.BoefjeTask, organisation_id: str, create_schedule: bool = True, caller: str = ""
    ) -> None:
        grace_period_passed = self.has_boefje_task_grace_period_passed(boefje_task)
        if not grace_period_passed:
            self.logger.debug(
                "Task has not passed grace period: %s",
                boefje_task.hash,
                task_hash=boefje_task.hash,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )
            return

        is_stalled = self.has_boefje_task_stalled(boefje_task)
        if is_stalled:
            self.logger.debug(
                "Task is stalled: %s",
                boefje_task.hash,
                task_hash=boefje_task.hash,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )

            # Update task in datastore to be failed
            task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(boefje_task.hash)
            task_db.status = models.TaskStatus.FAILED
            self.ctx.datastores.task_store.update_task(task_db)

        is_running = self.has_boefje_task_started_running(boefje_task)
        if is_running:
            self.logger.debug(
                "Task is still running: %s",
                boefje_task.hash,
                task_hash=boefje_task.hash,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )
            return

        if self.is_item_on_queue_by_hash(boefje_task.hash):
            self.logger.debug(
                "Task is already on queue: %s",
                boefje_task.hash,
                task_hash=boefje_task.hash,
                scheduler_id=self.scheduler_id,
                caller=caller,
                exc_info=True,
            )
            return

        task = models.Task(
            id=boefje_task.id,
            scheduler_id=self.scheduler_id,
            organisation=organisation_id,
            type=self.ITEM_TYPE.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
        )

        task.priority = self.ranker.rank(task)

        self.push_item_to_queue_with_timeout(item=task, max_tries=self.max_tries, create_schedule=create_schedule)

        self.logger.info(
            "Created boefje task",
            task_id=task.id,
            task_hash=task.hash,
            boefje_id=boefje_task.boefje.id,
            ooi_primary_key=boefje_task.input_ooi,
            scheduler_id=self.scheduler_id,
            organisation_id=organisation_id,
            caller=caller,
        )

    def push_item_to_queue(self, item: models.Task, create_schedule: bool = True) -> models.Task:
        """Some boefje scheduler specific logic before pushing the item to the
        queue."""
        boefje_task = models.BoefjeTask.model_validate(item.data)

        # Check if id's are unique and correctly set. Same id's are necessary
        # for the task runner.
        if item.id != boefje_task.id or self.ctx.datastores.task_store.get_task(item.id):
            new_id = uuid.uuid4()
            boefje_task.id = new_id
            item.id = new_id
            item.data = boefje_task.model_dump()

        return super().push_item_to_queue(item=item, create_schedule=create_schedule)

    def has_boefje_permission_to_run(self, boefje: models.Plugin, ooi: models.OOI) -> bool:
        """Checks whether a boefje is allowed to run on an ooi.

        Args:
            boefje: The boefje to check.
            ooi: The ooi to check.

        Returns:
            True if the boefje is allowed to run on the ooi, False otherwise.
        """
        if boefje.enabled is False:
            self.logger.debug(
                "Boefje: %s is disabled", boefje.name, boefje_id=boefje.id, scheduler_id=self.scheduler_id
            )
            return False

        boefje_scan_level = boefje.scan_level
        if boefje_scan_level is None:
            self.logger.warning(
                "No scan level found for boefje: %s", boefje.id, boefje_id=boefje.id, scheduler_id=self.scheduler_id
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
                scheduler_id=self.scheduler_id,
            )
            return False

        ooi_scan_level = ooi.scan_profile.level
        if ooi_scan_level is None:
            self.logger.warning(
                "No scan level found for ooi: %s",
                ooi.primary_key,
                ooi_primary_key=ooi.primary_key,
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
                scheduler_id=self.scheduler_id,
            )
            return False

        return True

    def has_boefje_task_started_running(self, task: models.BoefjeTask) -> bool:
        """Check if the same task is already running.

        Args:
            task: The BoefjeTask to check.

        Returns:
            True if the task is still running, False otherwise.
        """
        # Is task still running according to the datastore?
        task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(task.hash)
        if task_db is not None and task_db.status not in [models.TaskStatus.FAILED, models.TaskStatus.COMPLETED]:
            self.logger.debug(
                "Task is still running, according to the datastore", task_id=task_db.id, scheduler_id=self.scheduler_id
            )
            return True

        # Is task running according to bytes?
        task_bytes = self.ctx.services.bytes.get_last_run_boefje(
            boefje_id=task.boefje.id, input_ooi=task.input_ooi, organization_id=task.organization
        )

        # Task has been finished (failed, or succeeded) according to
        # the datastore, but we have no results of it in bytes, meaning
        # we have a problem. However when the grace period has been reached we
        # should not raise an error.
        if (
            task_bytes is None
            and task_db is not None
            and task_db.status in [models.TaskStatus.COMPLETED, models.TaskStatus.FAILED]
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
                scheduler_id=self.scheduler_id,
            )
            raise RuntimeError("Task has been finished, but no results found in bytes")

        if task_bytes is not None and task_bytes.ended_at is None and task_bytes.started_at is not None:
            self.logger.debug(
                "Task is still running, according to bytes", task_id=task_bytes.id, scheduler_id=self.scheduler_id
            )
            return True

        return False

    def has_boefje_task_stalled(self, task: models.BoefjeTask) -> bool:
        """Check if the same task is stalled.

        Args:
            task: The BoefjeTask to check.

        Returns:
            True if the task is stalled, False otherwise.
        """
        task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(task.hash)
        if (
            task_db is not None
            and task_db.status == models.TaskStatus.DISPATCHED
            and (
                task_db.modified_at is not None
                and datetime.now(timezone.utc)
                > task_db.modified_at + timedelta(seconds=self.ctx.config.pq_grace_period)
            )
        ):
            return True

        return False

    def has_boefje_task_grace_period_passed(self, task: models.BoefjeTask) -> bool:
        """Check if the grace period has passed for a task in both the
        datastore and bytes.

        NOTE: We don't check the status of the task since this needs to be done
        by checking if the task is still running or not.

        Args:
            task: Task to check.

        Returns:
            True if the grace period has passed, False otherwise.
        """
        # Does boefje have an interval specified?
        plugin = self.ctx.services.katalogus.get_plugin_by_id_and_org_id(task.boefje.id, task.organization)
        if plugin is not None and plugin.interval is not None and plugin.interval > 0:
            timeout = timedelta(minutes=plugin.interval)
        else:
            timeout = timedelta(seconds=self.ctx.config.pq_grace_period)

        task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(task.hash)

        # Has grace period passed according to datastore?
        if task_db is not None and datetime.now(timezone.utc) - task_db.modified_at < timeout:
            self.logger.debug(
                "Task has not passed grace period, according to the datastore",
                task_id=task_db.id,
                task_hash=task.hash,
                scheduler_id=self.scheduler_id,
            )
            return False

        task_bytes = self.ctx.services.bytes.get_last_run_boefje(
            boefje_id=task.boefje.id, input_ooi=task.input_ooi, organization_id=task.organization
        )

        # Did the grace period pass, according to bytes?
        if (
            task_bytes is not None
            and task_bytes.ended_at is not None
            and datetime.now(timezone.utc) - task_bytes.ended_at < timeout
        ):
            self.logger.debug(
                "Task has not passed grace period, according to bytes",
                task_id=task_bytes.id,
                task_hash=task.hash,
                scheduler_id=self.scheduler_id,
            )
            return False

        return True

    def get_boefjes_for_ooi(self, ooi: models.OOI, organisation: str) -> list[models.Plugin]:
        """Get available all boefjes (enabled and disabled) for an ooi.

        Args:
            ooi: The models.OOI to get boefjes for.

        Returns:
            A list of Plugin of type Boefje that can be run on the ooi.
        """
        boefjes = self.ctx.services.katalogus.get_boefjes_by_type_and_org_id(ooi.object_type, organisation)

        if boefjes is None:
            self.logger.debug(
                "No boefjes found for type: %s",
                ooi.object_type,
                input_ooi_primary_key=ooi.primary_key,
                scheduler_id=self.scheduler_id,
            )
            return []

        self.logger.debug(
            "Found %s boefjes for ooi: %s",
            len(boefjes),
            ooi,
            input_ooi_primary_key=ooi.primary_key,
            boefjes=[boefje.id for boefje in boefjes],
            scheduler_id=self.scheduler_id,
        )

        return boefjes

    def get_oois_for_boefje(self, boefje: models.Plugin, organisation: str) -> list[models.OOI]:
        oois = []

        oois_by_object_type = self.ctx.services.octopoes.get_objects_by_object_types(
            organisation,
            boefje.consumes,
            list(range(boefje.scan_level, 5)),  # type: ignore
        )

        # Filter OOIs based on permission
        for ooi in oois_by_object_type:
            if not self.has_boefje_permission_to_run(boefje, ooi):
                self.logger.debug(
                    "Boefje not allowed to run on ooi",
                    boefje_id=boefje.id,
                    ooi_primary_key=ooi.primary_key,
                    scheduler_id=self.scheduler_id,
                )
                continue
            oois.append(ooi)

        return oois

    def set_cron(self, item: models.Task) -> str | None:
        """Override Schedule.set_cron() when a boefje specifies a schedule for
        execution (cron expression) we schedule for its execution"""
        # Does a boefje have a schedule defined?
        plugin = self.ctx.services.katalogus.get_plugin_by_id_and_org_id(
            utils.deep_get(item.data, ["boefje", "id"]), item.organisation
        )
        if plugin is None or plugin.cron is None:
            return super().set_cron(item)

        return plugin.cron

    def calculate_deadline(self, task: models.Task) -> datetime:
        """Override Scheduler.calculate_deadline() to calculate the deadline
        for a task and based on the boefje interval."""
        # Does the boefje have an interval defined?
        plugin = self.ctx.services.katalogus.get_plugin_by_id_and_org_id(
            utils.deep_get(task.data, ["boefje", "id"]), task.organisation
        )
        if plugin is not None and plugin.interval is not None and plugin.interval > 0:
            return datetime.now(timezone.utc) + timedelta(minutes=plugin.interval)

        return super().calculate_deadline(task)
