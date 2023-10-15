import logging
from concurrent import futures
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Callable, List, Optional

import requests
from opentelemetry import trace

from scheduler import context, models, queues, rankers
from scheduler.connectors import listeners
from scheduler.models import (
    OOI,
    Boefje,
    BoefjeTask,
    MutationOperationType,
    Organisation,
    Plugin,
    PrioritizedItem,
    ScanProfileMutation,
    TaskStatus,
)

from .scheduler import Scheduler

tracer = trace.get_tracer(__name__)


class BoefjeScheduler(Scheduler):
    """A KAT specific implementation of a Boefje scheduler. It extends
    the `Scheduler` class by adding an `organisation` attribute.

    Attributes:
        logger: A logger instance.
        organisation: The organisation that this scheduler is for.
    """

    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        organisation: Organisation,
        queue: Optional[queues.PriorityQueue] = None,
        callback: Optional[Callable[..., None]] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.organisation: Organisation = organisation

        self.queue = queue or queues.BoefjePriorityQueue(
            pq_id=scheduler_id,
            maxsize=ctx.config.pq_maxsize,
            item_type=models.BoefjeTask,
            allow_priority_updates=True,
            pq_store=ctx.datastores.pq_store,
        )

        super().__init__(
            ctx=ctx,
            queue=self.queue,
            scheduler_id=scheduler_id,
            callback=callback,
        )

        self.ranker = rankers.BoefjeRanker(
            ctx=self.ctx,
        )

    def run(self) -> None:
        """The run method is called when the scheduler is started. It will
        start the listeners and the scheduling loops in separate threads. It
        is mainly tasked with populating the queue with tasks.

        * Scan profile mutations; when a scan profile is updated for an ooi
        e.g. the scan level is changed, we need to create new tasks for the
        ooi. We gather all boefjes that can run on the ooi and create tasks
        for them.

        * New boefjes; when new boefjes are added or enabled we find the ooi's
        that boefjes can run on, and create tasks for it.

        * Random OOI's from Octopoes; every minute we get a random OOI from
        Octopoes and create a task for it for the available boefjes for this
        OOI.
        """

        # Scan profile mutations
        listener = listeners.ScanProfileMutation(
            dsn=str(self.ctx.config.host_raw_data),
            queue=f"{self.organisation.id}__scan_profile_mutations",
            func=self.push_tasks_for_scan_profile_mutations,
            prefetch_count=self.ctx.config.rabbitmq_prefetch_count,
        )

        self.listeners["scan_profile_mutations"] = listener

        self.run_in_thread(
            name=f"scheduler-{self.scheduler_id}-mutations",
            target=self.listeners["scan_profile_mutations"].listen,
            loop=False,
        )

        # New Boefjes
        self.run_in_thread(
            name=f"scheduler-{self.scheduler_id}-new_boefjes",
            target=self.push_tasks_for_new_boefjes,
            interval=60.0,
        )

        # Random OOI's from Octopoes
        self.run_in_thread(
            name=f"scheduler-{self.scheduler_id}-random",
            target=self.push_tasks_for_random_objects,
            interval=60.0,
        )

    @tracer.start_as_current_span("boefje_push_tasks_for_scan_profile_mutations")
    def push_tasks_for_scan_profile_mutations(self, mutation: ScanProfileMutation) -> None:
        """Create tasks for oois that have a scan level change.

        Args:
            mutation: The mutation that was received.
        """
        self.logger.info(
            "Received scan level mutation %s for: %s [ooi_primary_key=%s, organisation_id=%s, scheduler_id=%s]",
            mutation.operation,
            mutation.primary_key,
            mutation.primary_key,
            self.organisation.id,
            self.scheduler_id,
        )

        # Should be an OOI in value
        ooi = mutation.value
        if ooi is None:
            self.logger.debug(
                "Mutation value is None, skipping [organisation_id=%s, scheduler_id=%s]",
                self.organisation.id,
                self.scheduler_id,
            )
            return

        if mutation.operation == MutationOperationType.DELETE:
            # When there are tasks of the ooi are on the queue, we need to
            # remove them from the queue.
            items, _ = self.ctx.datastores.pq_store.get_items(
                scheduler_id=self.scheduler_id,
                filters=[
                    models.Filter(
                        field="input_ooi",
                        operator="eq",
                        value=ooi.primary_key,
                    ),
                ],
            )

            # Delete all items for this ooi, update all tasks for this ooi
            # to cancelled.
            for item in items:
                self.ctx.datastores.pq_store.remove(
                    scheduler_id=self.scheduler_id,
                    item_id=item.id,
                )

                if item.hash is None:
                    continue

                task = self.ctx.datastores.task_store.get_latest_task_by_hash(item.hash)
                if task is None:
                    continue

                task.status = TaskStatus.CANCELLED
                self.ctx.datastores.task_store.update_task(task)

            return

        # What available boefjes do we have for this ooi?
        boefjes = self.get_boefjes_for_ooi(ooi)
        if not boefjes:
            self.logger.debug(
                "No boefjes available for %s [organisation_id=%s, scheduler_id=%s]",
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            return

        with futures.ThreadPoolExecutor() as executor:
            for boefje in boefjes:
                executor.submit(
                    self.push_task,
                    boefje,
                    ooi,
                    self.push_tasks_for_scan_profile_mutations.__name__,
                )

    @tracer.start_as_current_span("boefje_push_tasks_for_new_boefjes")
    def push_tasks_for_new_boefjes(self) -> None:
        """When new boefjes are added or enabled we find the ooi's that
        boefjes can run on, and create tasks for it."""
        new_boefjes = None
        try:
            new_boefjes = self.ctx.services.katalogus.get_new_boefjes_by_org_id(self.organisation.id)
        except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
            self.logger.warning(
                "Failed to get new boefjes for organisation: %s [organisation_id=%s, scheduler_id=%s]",
                self.organisation.name,
                self.organisation.id,
                self.scheduler_id,
            )
            return

        if new_boefjes is None or not new_boefjes:
            self.logger.debug(
                "No new boefjes for organisation: %s [organisation_id=%s, scheduler_id=%s]",
                self.organisation.name,
                self.organisation.id,
                self.scheduler_id,
            )
            return

        self.logger.debug(
            "Received new boefjes: %s [org_id=%s, scheduler_id=%s]",
            new_boefjes,
            self.organisation.id,
            self.scheduler_id,
        )

        for boefje in new_boefjes:
            oois_by_object_type: List[OOI] = []
            try:
                oois_by_object_type = self.ctx.services.octopoes.get_objects_by_object_types(
                    self.organisation.id,
                    boefje.consumes,
                    list(range(boefje.scan_level, 5)),
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get oois for organisation: %s [organisation_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            with futures.ThreadPoolExecutor() as executor:
                for ooi in oois_by_object_type:
                    executor.submit(
                        self.push_task,
                        boefje,
                        ooi,
                        self.push_tasks_for_new_boefjes.__name__,
                    )

    @tracer.start_as_current_span("boefje_push_tasks_for_random_objects")
    def push_tasks_for_random_objects(self) -> None:
        """Push tasks for random ooi's from octopoes to the queue."""
        if self.queue.full():
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks "
                "[queue_qsize=%d, organisation_id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

        try:
            random_oois = self.ctx.services.octopoes.get_random_objects(
                organisation_id=self.organisation.id,
                n=self.ctx.config.pq_max_random_objects,
                scan_level=[1, 2, 3, 4],
            )
        except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
            self.logger.warning(
                "Could not get random oois for organisation: %s [organisation_id=%s, scheduler_id=%s]",
                self.organisation.name,
                self.organisation.id,
                self.scheduler_id,
            )
            return

        if not random_oois:
            self.logger.debug(
                "No random oois for organisation: %s [organisation_id=%s, scheduler_id=%s]",
                self.organisation.name,
                self.organisation.id,
                self.scheduler_id,
            )
            return

        for ooi in random_oois:
            self.logger.debug(
                "Checking random ooi %s for rescheduling of tasks [organisation_id=%s, scheduler_id=%s]",
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )

            boefjes = self.get_boefjes_for_ooi(ooi)
            if boefjes is None or not boefjes:
                self.logger.debug(
                    "No boefjes available for ooi %s, skipping [organisation_id=%s, scheduler_id=%s]",
                    ooi,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            with futures.ThreadPoolExecutor() as executor:
                for boefje in boefjes:
                    executor.submit(
                        self.push_task,
                        boefje,
                        ooi,
                        self.push_tasks_for_random_objects.__name__,
                    )

    @tracer.start_as_current_span("boefje_is_task_allowed_to_run")
    def is_task_allowed_to_run(self, boefje: Plugin, ooi: OOI) -> bool:
        """Checks whether a boefje is allowed to run on an ooi.

        Args:
            boefje: The boefje to check.
            ooi: The ooi to check.

        Returns:
            True if the boefje is allowed to run on the ooi, False otherwise.
        """
        if boefje.enabled is False:
            self.logger.debug(
                "Boefje: %s is disabled [boefje_id=%s, organisation_id=%s, scheduler_id=%s]",
                boefje.name,
                boefje.id,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        if ooi.scan_profile is None:
            self.logger.debug(
                "No scan_profile found for ooi: %s "
                "[ooi_primary_key=%s, ooi_scan_profile=%s, organisation_id=%s, scheduler_id=%s]",
                ooi.primary_key,
                ooi,
                ooi.scan_profile,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        ooi_scan_level = ooi.scan_profile.level
        if ooi_scan_level is None:
            self.logger.warning(
                "No scan level found for ooi: %s [ooi_primary_key=%s, organisation_id=%s, scheduler_id=%s]",
                ooi.primary_key,
                ooi,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        boefje_scan_level = boefje.scan_level
        if boefje_scan_level is None:
            self.logger.warning(
                "No scan level found for boefje: %s [boefje_id=%s, organisation_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje.id,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        # Boefje intensity score ooi clearance level, range
        # from 0 to 4. 4 being the highest intensity, and 0 being
        # the lowest. OOI clearance level defines what boefje
        # intensity is allowed to run on.
        if boefje_scan_level > ooi_scan_level:
            self.logger.debug(
                "Boefje: %s scan level %s is too intense for ooi: %s scan level %s "
                "[boefje_id=%s, ooi_primary_key=%s, organisation_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje_scan_level,
                ooi.primary_key,
                ooi_scan_level,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        return True

    @tracer.start_as_current_span("boefje_is_task_running")
    def is_task_running(self, task: BoefjeTask) -> bool:
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
            self.logger.warning(
                "Could not get latest task by hash: %s [organisation_id=%s, scheduler_id=%s]",
                task.hash,
                self.organisation.id,
                self.scheduler_id,
                exc_info=exc_db,
            )
            raise exc_db

        if task_db is not None and task_db.status not in [TaskStatus.FAILED, TaskStatus.COMPLETED]:
            self.logger.debug(
                "Task is still running, according to the datastore "
                "[task_id=%s, task_hash=%s, organisation_id=%s, scheduler_id=%s]",
                task_db.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            return True

        # Is task running according to bytes?
        try:
            task_bytes = self.ctx.services.bytes.get_last_run_boefje(
                boefje_id=task.boefje.id,
                input_ooi=task.input_ooi,
                organization_id=task.organization,
            )
        except Exception as exc_bytes:
            self.logger.error(
                "Failed to get last run boefje from bytes "
                "[boefje_id=%s, input_primary_key=%s, organisation_id=%s, scheduler_id=%s, exc=%s]",
                task.boefje.id,
                task.input_ooi,
                self.organisation.id,
                self.scheduler_id,
                exc_bytes,
            )
            raise exc_bytes

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
                "this error. "
                "[task_id=%s, task_hash=%s, organisation_id=%s, scheduler_id=%s]",
                task_db.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            raise RuntimeError("Task has been finished, but no results found in bytes")

        if task_bytes is not None and task_bytes.ended_at is None and task_bytes.started_at is not None:
            self.logger.debug(
                "Task is still running, according to bytes "
                "[task_id=%s, task_hash=%s, organisation_id=%s, scheduler_id=%s]",
                task_bytes.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            return True

        return False

    @tracer.start_as_current_span("boefje_is_task_stalled")
    def is_task_stalled(self, task: BoefjeTask) -> bool:
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
                "Could not get latest task by hash: %s [organisation_id=%s, scheduler_id=%s]",
                task.hash,
                self.organisation.id,
                self.scheduler_id,
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

    @tracer.start_as_current_span("boefje_push_task")
    def push_task(self, boefje: Plugin, ooi: OOI, caller: str = "") -> None:
        """Given a Boefje and OOI create a BoefjeTask and push it onto
        the queue.

        Args:
            boefje: Boefje to run.
            ooi: OOI to run Boefje on.
            caller: The name of the function that called this function, used for logging.

        """
        task = BoefjeTask(
            boefje=Boefje.parse_obj(boefje.dict()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        if not self.is_task_allowed_to_run(boefje, ooi):
            self.logger.debug(
                "Task is not allowed to run: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
            )
            return

        try:
            grace_period_passed = self.has_grace_period_passed(task)
            if not grace_period_passed:
                self.logger.debug(
                    "Task has not passed grace period: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                    task,
                    self.organisation.id,
                    self.scheduler_id,
                    caller,
                )
                return
        except Exception as exc_grace_period:
            self.logger.warning(
                "Could not check if grace period has passed: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
                exc_info=exc_grace_period,
            )
            return

        try:
            is_stalled = self.is_task_stalled(task)
            if is_stalled:
                self.logger.debug(
                    "Task is stalled: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                    task,
                    self.organisation.id,
                    self.scheduler_id,
                    caller,
                )

                # Update task in datastore to be failed
                task_db = self.ctx.datastores.task_store.get_latest_task_by_hash(task.hash)
                task_db.status = TaskStatus.FAILED
                self.ctx.datastores.task_store.update_task(task_db)
        except Exception as exc_stalled:
            self.logger.warning(
                "Could not check if task is stalled: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
                exc_info=exc_stalled,
            )
            return

        try:
            is_running = self.is_task_running(task)
            if is_running:
                self.logger.debug(
                    "Task is still running: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                    task,
                    self.organisation.id,
                    self.scheduler_id,
                    caller,
                )
                return
        except Exception as exc_running:
            self.logger.warning(
                "Could not check if task is running: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
                exc_info=exc_running,
            )
            return

        if self.is_item_on_queue_by_hash(task.hash):
            self.logger.debug(
                "Task is already on queue: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
            )
            return

        prior_tasks = self.ctx.datastores.task_store.get_tasks_by_hash(task.hash)
        score = self.ranker.rank(
            SimpleNamespace(
                prior_tasks=prior_tasks,
                task=task,
            )
        )

        # We need to create a PrioritizedItem for this task, to push
        # it to the priority queue.
        p_item = PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler_id,
            priority=score,
            data=task.model_dump(),
            hash=task.hash,
        )

        try:
            self.push_item_to_queue_with_timeout(p_item, self.max_tries)
        except queues.QueueFullError:
            self.logger.warning(
                "Could not add task to queue, queue was full: %s "
                "[queue_qsize=%d, queue_maxsize=%d, organisation_id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.queue.qsize(),
                self.queue.maxsize,
                self.organisation.id,
                self.scheduler_id,
                caller,
            )
            return

        self.logger.info(
            "Created boefje task: %s for ooi: %s "
            "[boefje_id=%s, ooi_primary_key=%s, organisation_id=%s, scheduler_id=%s, caller=%s]",
            task,
            ooi.primary_key,
            boefje.id,
            ooi.primary_key,
            self.organisation.id,
            self.scheduler_id,
            caller,
        )

    @tracer.start_as_current_span("boefje_has_grace_period_passed")
    def has_grace_period_passed(self, task: BoefjeTask) -> bool:
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
                "Could not get latest task by hash: %s [task_hash=%s, organisation_id=%s, scheduler_id=%s]",
                task.hash,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
                exc_info=exc_db,
            )
            raise exc_db

        # Has grace period passed according to datastore?
        if task_db is not None and datetime.now(timezone.utc) - task_db.modified_at < timedelta(
            seconds=self.ctx.config.pq_grace_period
        ):
            self.logger.debug(
                "Task has not passed grace period, according to the datastore "
                "[task_id=%s, task_hash=%s, organisation_id=%s, scheduler_id=%s]",
                task_db.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        try:
            task_bytes = self.ctx.services.bytes.get_last_run_boefje(
                boefje_id=task.boefje.id,
                input_ooi=task.input_ooi,
                organization_id=task.organization,
            )
        except Exception as exc_bytes:
            self.logger.error(
                "Failed to get last run boefje from bytes "
                "[task_boefje_id=%s, task_input_ooi=%s, organisation_id=%s, scheduler_id=%s, exc=%s]",
                task.boefje.id,
                task.input_ooi,
                self.organisation.id,
                self.scheduler_id,
                exc_bytes,
            )
            raise exc_bytes

        # Did the grace period pass, according to bytes?
        if (
            task_bytes is not None
            and task_bytes.ended_at is not None
            and datetime.now(timezone.utc) - task_bytes.ended_at < timedelta(seconds=self.ctx.config.pq_grace_period)
        ):
            self.logger.debug(
                "Task has not passed grace period, according to bytes "
                "[task_id=%s, task_hash=%s, organisation_id=%s, scheduler_id=%s]",
                task_bytes.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        return True

    def get_boefjes_for_ooi(self, ooi) -> List[Plugin]:
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
        except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
            self.logger.warning(
                "Could not get boefjes for object_type: %s [ooi_object_type=%s, organisation_id=%s, scheduler_id=%s]",
                ooi.object_type,
                ooi.object_type,
                self.organisation.id,
                self.scheduler_id,
            )
            return []

        if boefjes is None:
            self.logger.debug(
                "No boefjes found for type: %s [ooi=%s, organisation_id=%s, scheduler_id=%s]",
                ooi.object_type,
                ooi,
                self.organisation.id,
                self.scheduler_id,
            )
            return []

        self.logger.debug(
            "Found %s boefjes for ooi: %s [ooi=%s, boefjes=%s, organisation_id=%s, scheduler_id=%s]",
            len(boefjes),
            ooi,
            ooi,
            [boefje.id for boefje in boefjes],
            self.organisation.id,
            self.scheduler_id,
        )

        return boefjes
