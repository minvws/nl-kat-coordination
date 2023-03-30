import logging
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import List

import pika
import requests

from scheduler import context, queues, rankers
from scheduler.models import OOI, Boefje, BoefjeTask, Organisation, Plugin, PrioritizedItem, TaskStatus

from .scheduler import Scheduler


class BoefjeScheduler(Scheduler):
    """A KAT specific implementation of a Boefje scheduler. It extends
    the `Scheduler` class by adding a `organisation` attribute.

    Attributes:
        organisation: The organisation that this scheduler is for.
    """

    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        queue: queues.PriorityQueue,
        ranker: rankers.Ranker,
        organisation: Organisation,
        populate_queue_enabled: bool = True,
    ):
        super().__init__(
            ctx=ctx,
            scheduler_id=scheduler_id,
            queue=queue,
            ranker=ranker,
            populate_queue_enabled=populate_queue_enabled,
        )

        self.logger = logging.getLogger(__name__)
        self.organisation: Organisation = organisation

    def populate_queue(self) -> None:
        """Populate the PriorityQueue.

        While the queue is not full we will try to fill it with items that have
        been created, e.g. when the scan level was increased (since oois start
        with a scan level 0 and will not start any boefjes).

        When this is done we will try and fill the rest of the queue with
        random items from octopoes and schedule them accordingly.
        """
        self.push_tasks_for_scan_profile_mutations()

        self.push_tasks_for_random_objects()

    def push_tasks_for_scan_profile_mutations(self) -> None:
        """Create tasks for oois that have a scan level change.

        We loop until we don't have any messages on the queue anymore.
        """
        while not self.queue.full():
            time.sleep(1)

            mutation = None
            try:
                mutation = self.ctx.services.scan_profile_mutation.get_scan_profile_mutation(
                    queue=f"{self.organisation.id}__scan_profile_mutations",
                )
            except (
                pika.exceptions.ConnectionClosed,
                pika.exceptions.ChannelClosed,
                pika.exceptions.ChannelClosedByBroker,
                pika.exceptions.AMQPConnectionError,
            ) as e:
                self.logger.debug(
                    "Could not connect to rabbitmq queue: %s [organisation.id=%s, scheduler_id=%s]",
                    f"{self.organisation.id}__scan_profile_mutations",
                    self.organisation.id,
                    self.scheduler_id,
                )
                if self.stop_event.is_set():
                    raise e

            # Stop the loop when we've processed everything from the
            # messaging queue, so we can continue to the next step.
            if mutation is None:
                self.logger.debug(
                    "No more mutation left on queue, processed everything [orgnisation.id=%s, scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                return

            self.logger.debug(
                "Received scan level mutation %s for: %s [ooi.primary_key=%s, organisation.id=%s, scheduler_id=%s]",
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
                    "Mutation value is None, skipping %s [organisation.id=%s, scheduler_id=%s]",
                    mutation,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            # What available boefjes do we have for this ooi?
            boefjes = self.get_boefjes_for_ooi(ooi)
            if boefjes is None or len(boefjes) == 0:
                self.logger.debug(
                    "No boefjes available for ooi %s, skipping [organisation.id=%s, scheduler_id=%s]",
                    mutation.value,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            # Create a task for each boefje for this ooi and push it onto the
            # queue.
            for boefje in boefjes:
                task = BoefjeTask(
                    boefje=Boefje(id=boefje.id, version=boefje.version),
                    input_ooi=ooi.primary_key,
                    organization=self.organisation.id,
                )

                if not self.is_task_allowed_to_run(boefje, ooi):
                    self.logger.debug(
                        "Task is not allowed to run: %s [organisation.id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                try:
                    is_running = self.is_task_running(task)
                    if is_running:
                        self.logger.debug(
                            "Task is already running: %s [organisation.id=%s, scheduler_id=%s]",
                            task,
                            self.organisation.id,
                            self.scheduler_id,
                        )
                        continue
                except Exception as exc_running:
                    self.logger.warning(
                        "Could not check if task is running: %s [organisation.id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                        exc_info=exc_running,
                    )
                    continue

                try:
                    grace_period_passed = self.has_grace_period_passed(task)
                    if not grace_period_passed:
                        self.logger.debug(
                            "Task has not passed grace period: %s [organisation.id=%s, scheduler_id=%s]",
                            task,
                            self.organisation.id,
                            self.scheduler_id,
                        )
                        continue
                except Exception as exc_grace_period:
                    self.logger.warning(
                        "Could not check if grace period has passed: %s [organisation.id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                        exc_info=exc_grace_period,
                    )
                    continue

                if self.queue.is_item_on_queue_by_hash(task.hash):
                    self.logger.debug(
                        "Task is already on queue: %s [organisation.id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                prior_tasks = self.ctx.task_store.get_tasks_by_hash(task.hash)
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
                    data=task,
                    hash=task.hash,
                )

                while not self.is_space_on_queue():
                    self.logger.debug(
                        "Waiting for queue to have enough space, not adding task to queue "
                        "[queue.qsize=%d, queue.maxsize=%d, organisation.id=%s, scheduler_id=%s]",
                        self.queue.qsize(),
                        self.queue.maxsize,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    time.sleep(1)

                self.logger.info(
                    "Created boefje task: %s for ooi: %s "
                    "[boefje.id=%s, ooi.primary_key=%s, organisation.id=%s, scheduler_id=%s]",
                    boefje.name,
                    ooi.primary_key,
                    boefje.id,
                    ooi.primary_key,
                    self.organisation.id,
                    self.scheduler_id,
                )

                self.push_item_to_queue(p_item)
        else:
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks "
                "[queue.qsize=%d, organisation.id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

    def push_tasks_for_random_objects(self) -> None:
        """Push tasks for random objects from octopoes to the queue."""
        if self.queue.full():
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks "
                "[queue.qsize=%d, organisation.id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

        try:
            random_oois = self.ctx.services.octopoes.get_random_objects(
                organisation_id=self.organisation.id,
                n=self.ctx.config.pq_populate_max_random_objects,
            )
        except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
            self.logger.warning(
                "Could not get random oois for organisation: %s [organisation.id=%s, scheduler_id=%s]",
                self.organisation.name,
                self.organisation.id,
                self.scheduler_id,
            )
            return

        if not random_oois:
            self.logger.debug(
                "No random oois for organisation: %s [organisation.id=%s, scheduler_id=%s]",
                self.organisation.name,
                self.organisation.id,
                self.scheduler_id,
            )
            return

        for ooi in random_oois:
            self.logger.debug(
                "Checking random ooi %s for rescheduling of tasks [organisation.id=%s, scheduler_id=%s]",
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )

            boefjes = self.get_boefjes_for_ooi(ooi)
            if boefjes is None or not boefjes:
                self.logger.debug(
                    "No boefjes available for ooi %s, skipping [organisation.id=%s, scheduler_id=%s]",
                    ooi,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            for boefje in boefjes:
                task = BoefjeTask(
                    boefje=Boefje.parse_obj(boefje),
                    input_ooi=ooi.primary_key,
                    organization=self.organisation.id,
                )

                if not self.is_task_allowed_to_run(boefje, ooi):
                    self.logger.debug(
                        "Task is not allowed to run: %s [organisation.id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                try:
                    is_running = self.is_task_running(task)
                    if is_running:
                        self.logger.debug(
                            "Task is already running: %s [organisation.id=%s, scheduler_id=%s]",
                            task,
                            self.organisation.id,
                            self.scheduler_id,
                        )
                        continue
                except Exception as exc_running:
                    self.logger.warning(
                        "Could not check if task is running: %s [organisation.id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                        exc_info=exc_running,
                    )
                    continue

                try:
                    grace_period_passed = self.has_grace_period_passed(task)
                    if not grace_period_passed:
                        self.logger.debug(
                            "Task has not passed grace period: %s [organisation.id=%s, scheduler_id=%s]",
                            task,
                            self.organisation.id,
                            self.scheduler_id,
                        )
                        continue
                except Exception as exc_grace_period:
                    self.logger.warning(
                        "Could not check if grace period has passed: %s [organisation.id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                        exc_info=exc_grace_period,
                    )
                    continue

                if self.queue.is_item_on_queue_by_hash(task.hash):
                    self.logger.debug(
                        "Task is already on queue: %s [organisation.id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                prior_tasks = self.ctx.task_store.get_tasks_by_hash(task.hash)
                score = self.ranker.rank(
                    SimpleNamespace(
                        prior_tasks=prior_tasks,
                        task=task,
                    )
                )
                # We need to create a PrioritizedItem for this task, to
                # push it to the priority queue.
                p_item = PrioritizedItem(
                    id=task.id,
                    scheduler_id=self.scheduler_id,
                    priority=score,
                    data=task,
                    hash=task.hash,
                )

                while not self.is_space_on_queue():
                    self.logger.debug(
                        "Waiting for queue to have enough space, not adding task to queue "
                        "[queue.qsize=%d, queue.maxsize=%d, organisation.id=%s, scheduler_id=%s]",
                        self.queue.qsize(),
                        self.queue.maxsize,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    time.sleep(1)

                self.logger.info(
                    "Created rescheduled boefje task: %s for ooi: %s "
                    "[boefje.id=%s, ooi.primary_key=%s, organisation.id=%s, scheduler_id=%s]",
                    boefje.name,
                    ooi.primary_key,
                    boefje.id,
                    ooi.primary_key,
                    self.organisation.id,
                    self.scheduler_id,
                )

                self.push_item_to_queue(p_item)

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
                "Boefje: %s is disabled [organisation.id=%s, boefje.id=%s, organisation.id=%s, scheduler_id=%s]",
                boefje.name,
                self.organisation.id,
                boefje.id,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        if ooi.scan_profile is None:
            self.logger.debug(
                "No scan_profile found for ooi: %s "
                "[ooi.primary_key=%s, ooi.scan_profile=%s, organisation.id=%s, scheduler_id=%s]",
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
                "No scan level found for ooi: %s [ooi.primary_key=%s, organisation.id=%s, scheduler_id=%s]",
                ooi.primary_key,
                ooi,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        boefje_scan_level = boefje.scan_level
        if boefje_scan_level is None:
            self.logger.warning(
                "No scan level found for boefje: %s [boefje.id=%s, organisation.id=%s, scheduler_id=%s]",
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
                "[boefje.id=%s, ooi.primary_key=%s, organisation.id=%s, scheduler_id=%s]",
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

    def is_task_running(self, task: BoefjeTask) -> bool:
        # Get the last tasks that have run or are running for the hash
        # of this particular BoefjeTask.
        try:
            task_db = self.ctx.task_store.get_latest_task_by_hash(task.hash)
        except Exception as exc_db:
            self.logger.warning(
                "Could not get latest task by hash: %s [organisation.id=%s, scheduler_id=%s]",
                task.hash,
                self.organisation.id,
                self.scheduler_id,
                exc_info=exc_db,
            )
            raise exc_db

        try:
            task_bytes = self.ctx.services.bytes.get_last_run_boefje(
                boefje_id=task.boefje.id,
                input_ooi=task.input_ooi,
                organization_id=task.organization,
            )
        except Exception as exc_bytes:
            self.logger.error(
                "Failed to get last run boefje from bytes "
                "[boefje.id=%s, input.primary_key=%s, organisation.id=%s, scheduler_id=%s, exc=%s]",
                task.boefje.id,
                task.input_ooi,
                self.organisation.id,
                self.scheduler_id,
                exc_bytes,
            )
            raise exc_bytes

        # Is task still running according to the datastore?
        if (
            task_db is not None
            and task_bytes is None
            and task_db.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        ):
            self.logger.debug(
                "Task is still running, according to the datastore "
                "[task.id=%s, task.hash=%s, organisation.id=%s, scheduler_id=%s]",
                task_db.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            return True

        # Task has been finished (failed, or succeeded) according to
        # the database, but we have no results of it in bytes, meaning
        # we have a problem.
        if task_bytes is None and task_db is not None and task_db.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            self.logger.error(
                "Task has been finished, but no results found in bytes "
                "[task.id=%s, task.hash=%s, organisation.id=%s, scheduler_id=%s]",
                task_db.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            raise RuntimeError("Task has been finished, but no results found in bytes")

        # Is boefje still running according to bytes?
        if task_bytes is not None and task_bytes.ended_at is None and task_bytes.started_at is not None:
            self.logger.debug(
                "Task is still running, according to bytes "
                "[task.id=%s, task.hash=%s, organisation.id=%s, scheduler_id=%s]",
                task_bytes.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            return True

        return False

    def has_grace_period_passed(self, task: BoefjeTask) -> bool:
        """Check if the grace period has passed for a task in both the
        datastore and bytes.

        NOTE: We don't check the status of the task since this needs to be done
        by checking if the task is still running or not.
        """
        try:
            task_db = self.ctx.task_store.get_latest_task_by_hash(task.hash)
        except Exception as exc_db:
            self.logger.warning(
                "Could not get latest task by hash: %s [task.hash=%s, organisation.id=%s, scheduler_id=%s]",
                task.hash,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
                exc_info=exc_db,
            )
            raise exc_db

        # Has grace period passed according to datastore?
        if task_db is not None and datetime.now(timezone.utc) - task_db.modified_at < timedelta(
            seconds=self.ctx.config.pq_populate_grace_period
        ):
            self.logger.debug(
                "Task has not passed grace period, according to the datastore "
                "[task.id=%s, task.hash=%s, organisation.id=%s, scheduler_id=%s]",
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
                "[task.boefje.id=%s, task.input_ooi=%s, organisation.id=%s, scheduler_id=%s, exc=%s]",
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
            and datetime.now(timezone.utc) - task_bytes.ended_at
            < timedelta(seconds=self.ctx.config.pq_populate_grace_period)
        ):
            self.logger.debug(
                "Task has not passed grace period, according to bytes "
                "[task.id=%s, task.hash=%s, organisation.id=%s, scheduler_id=%s]",
                task_bytes.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        return True

    def is_space_on_queue(self) -> bool:
        """Check if there is space on the queue.

        NOTE: maxsize 0 means unlimited
        """
        if (self.queue.maxsize - self.queue.qsize()) <= 0 and self.queue.maxsize != 0:
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
                "Could not get boefjes for object_type: %s [ooi.object_type=%s, organisation.id=%s, scheduler_id=%s]",
                ooi.object_type,
                ooi.object_type,
                self.organisation.id,
                self.scheduler_id,
            )
            return []

        if boefjes is None:
            self.logger.debug(
                "No boefjes found for type: %s [ooi=%s, organisation.id=%s, scheduler_id=%s]",
                ooi.object_type,
                ooi,
                self.organisation.id,
                self.scheduler_id,
            )
            return []

        self.logger.debug(
            "Found %s boefjes for ooi: %s [ooi=%s, boefjes=%s, organisation.id=%s, scheduler_id=%s]",
            len(boefjes),
            ooi,
            ooi,
            [boefje.id for boefje in boefjes],
            self.organisation.id,
            self.scheduler_id,
        )

        return boefjes
