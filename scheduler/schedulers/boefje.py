import time
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import List

import pika
import requests

from scheduler import context, dispatchers, queues, rankers
from scheduler.models import OOI, Boefje, BoefjeTask, Organisation

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
        dispatcher: dispatchers.Dispatcher,
        organisation: Organisation,
        populate_queue_enabled: bool = True,
    ):
        super().__init__(
            ctx=ctx,
            scheduler_id=scheduler_id,
            queue=queue,
            ranker=ranker,
            dispatcher=dispatcher,
            populate_queue_enabled=populate_queue_enabled,
        )

        self.organisation: Organisation = organisation

    def populate_queue(self) -> None:
        """Populate the PriorityQueue.

        While the queue is not full we will try to fill it with items that have
        been created, e.g. when the scan level was increased (since oois start
        with a scan level 0 and will not start any boefjes).

        When this is done we will try and fill the rest of the queue with
        random items from octopoes and schedule them accordingly.
        """
        while not self.queue.full():
            time.sleep(1)

            try:
                latest_ooi = self.ctx.services.scan_profile.get_latest_object(
                    queue=f"{self.organisation.id}__scan_profile_increments",
                )
            except (
                pika.exceptions.ConnectionClosed,
                pika.exceptions.ChannelClosed,
                pika.exceptions.ChannelClosedByBroker,
                pika.exceptions.AMQPConnectionError,
            ) as e:
                self.logger.warning(
                    "Could not connect to rabbitmq queue: %s [org_id=%s, scheduler_id=%s]",
                    f"{self.organisation.id}__scan_profile_increments",
                    self.organisation.id,
                    self.scheduler_id,
                )
                if self.stop_event.is_set():
                    raise e

                time.sleep(60)
                return

            if latest_ooi is None:
                self.logger.debug(
                    "No latest oois for organisation: %s [org_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    self.organisation.id,
                    self.scheduler_id,
                )
                break

            # From ooi's create prioritized items (tasks) to push onto queue
            # continue with the next object (when there are more objects)
            # to see if there are more tasks to add.
            p_items = self.create_tasks_for_oois([latest_ooi])
            if len(p_items) == 0:
                continue

            # NOTE: maxsize 0 means unlimited
            while len(p_items) > (self.queue.maxsize - self.queue.pq.qsize()) and self.queue.maxsize != 0:
                self.logger.debug(
                    "Waiting for queue to have enough space, not adding %d tasks to queue [qsize=%d, maxsize=%d, org_id=%s, scheduler_id=%s]",
                    len(p_items),
                    self.queue.pq.qsize(),
                    self.queue.maxsize,
                    self.organisation.id,
                    self.scheduler_id,
                )
                time.sleep(1)

            self.add_p_items_to_queue(p_items)
        else:
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks [qsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.pq.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

        tries = 0
        while not self.queue.full():
            time.sleep(1)

            try:
                random_oois = self.ctx.services.octopoes.get_random_objects(
                    organisation_id=self.organisation.id,
                    n=10,
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get random oois for organisation: %s [org_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    self.organisation.id,
                    self.scheduler_id,
                )
                return

            if len(random_oois) == 0:
                self.logger.debug(
                    "No random oois for organisation: %s [org_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    self.organisation.id,
                    self.scheduler_id,
                )
                break

            # NOTE: It is possible that a random ooi will not generate any
            # tasks, for instance when all ooi's and their boefjes have already
            # run. When this happens 3 times in a row we will break out
            # of the loop. We reset the tries counter to 0 when we do
            # get new tasks from an ooi.
            p_items = self.create_tasks_for_oois(random_oois)
            if len(p_items) == 0 and tries < 3:
                tries += 1
                continue
            elif len(p_items) == 0 and tries >= 3:
                self.logger.warning(
                    "No random oois for organisation: %s [tries=%d, org_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    tries,
                    self.organisation.id,
                    self.scheduler_id,
                )
                break

            # NOTE: maxsize 0 means unlimited
            while len(p_items) > (self.queue.maxsize - self.queue.pq.qsize()) and self.queue.maxsize != 0:
                self.logger.debug(
                    "Waiting for queue to have enough space, not adding %d tasks to queue [qsize=%d, maxsize=%d, org_id=%s, scheduler_id=%s]",
                    len(p_items),
                    self.queue.pq.qsize(),
                    self.queue.maxsize,
                    self.organisation.id,
                    self.scheduler_id,
                )
                time.sleep(1)

            self.add_p_items_to_queue(p_items)
            tries = 0
        else:
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks [qsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.pq.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

    def create_tasks_for_oois(self, oois: List[OOI]) -> List[queues.PrioritizedItem]:
        """For every provided ooi we will create available and enabled boefje
        tasks.

        Args:
            oois: A list of OOIs.

        Returns:
            A list of BoefjeTasks.
        """
        p_items: List[queues.PrioritizedItem] = []
        for ooi in oois:
            try:
                boefjes = self.ctx.services.katalogus.get_boefjes_by_type_and_org_id(
                    ooi.object_type,
                    self.organisation.id,
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get boefjes for object_type: %s [object_type=%s, org_id=%s, scheduler_id=%s]",
                    ooi.object_type,
                    ooi.object_type,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            if boefjes is None:
                self.logger.debug(
                    "No boefjes found for type: %s [ooi=%s, org_id=%s, scheduler_id=%s]",
                    ooi.object_type,
                    ooi,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            self.logger.debug(
                "Found %s boefjes for ooi: %s [ooi=%s, boefjes=%s, org_id=%s, scheduler_id=%s]",
                len(boefjes),
                ooi,
                ooi,
                [boefje.id for boefje in boefjes],
                self.organisation.id,
                self.scheduler_id,
            )

            for boefje in boefjes:
                if boefje.enabled is False:
                    self.logger.debug(
                        "Boefje: %s is disabled [org_id=%s, boefje_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.name,
                        self.organisation.id,
                        boefje.id,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                task = BoefjeTask(
                    id=uuid.uuid4().hex,
                    boefje=Boefje.parse_obj(boefje),
                    input_ooi=ooi.primary_key,
                    organization=self.organisation.id,
                )

                if ooi.scan_profile is None:
                    self.logger.debug(
                        "No scan_profile found for ooi: %s [ooi_id=%s, scan_profile=%s, org_id=%s, scheduler_id=%s]",
                        ooi.primary_key,
                        ooi,
                        ooi.scan_profile,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                ooi_scan_level = ooi.scan_profile.level
                if ooi_scan_level is None:
                    self.logger.warning(
                        "No scan level found for ooi: %s [ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        ooi.primary_key,
                        ooi,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                boefje_scan_level = boefje.scan_level
                if boefje_scan_level is None:
                    self.logger.warning(
                        "No scan level found for boefje: %s [boefje_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje.id,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                # Boefje intensity score ooi clearance level, range
                # from 0 to 4. 4 being the highest intensity, and 0 being
                # the lowest. OOI clearance level defines what boefje
                # intesity is allowed to run on.
                if boefje_scan_level > ooi_scan_level:
                    self.logger.debug(
                        "Boefje: %s scan level %s is too intense for ooi: %s scan level %s [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje_scan_level,
                        ooi.primary_key,
                        ooi_scan_level,
                        boefje.id,
                        ooi.primary_key,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                # We don't want the populator to add/update tasks to the
                # queue, when they are already on there. However, we do
                # want to allow the api to update the priority. So we
                # created the queue with allow_priority_updates=True
                # regardless. When the ranker is updated to correctly rank
                # tasks, we can allow the populator to also update the
                # priority. Then remove the following:
                if self.queue.is_item_on_queue(task):
                    self.logger.debug(
                        "Boefje: %s is already on queue [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje.id,
                        ooi.primary_key,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                # Boefjes should not run before the grace period ends, thus
                # we will check when the combination boefje and ooi was last
                # run.
                try:
                    last_run_boefje = self.ctx.services.bytes.get_last_run_boefje(
                        boefje_id=boefje.id,
                        input_ooi=ooi.primary_key,
                        organization_id=self.organisation.id,
                    )
                except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                    self.logger.warning(
                        "Could not get last run boefje for boefje: %s with ooi: %s [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.name,
                        ooi.primary_key,
                        boefje.id,
                        ooi.primary_key,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                if (
                    last_run_boefje is not None
                    and last_run_boefje.ended_at is None
                    and last_run_boefje.start_time is not None
                ):
                    self.logger.debug(
                        "Boefje %s is already running [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje.id,
                        ooi.primary_key,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                if (
                    last_run_boefje is not None
                    and last_run_boefje.ended_at is not None
                    and datetime.now(timezone.utc) - last_run_boefje.ended_at
                    < timedelta(seconds=self.ctx.config.pq_populate_grace_period)
                ):
                    self.logger.debug(
                        "Boefje: %s already run for input ooi %s [last_run_boefje=%s, org_id=%s, scheduler_id=%s]",
                        boefje.id,
                        ooi.primary_key,
                        last_run_boefje,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                score = self.ranker.rank(SimpleNamespace(last_run_boefje=last_run_boefje, task=task))
                if score < 0:
                    self.logger.warning(
                        "Score too low for boefje: %s and input ooi: %s [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.id,
                        ooi.primary_key,
                        boefje.id,
                        ooi.primary_key,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                p_items.append(queues.PrioritizedItem(priority=score, item=task))

        return p_items
