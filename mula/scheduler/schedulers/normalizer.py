import logging
import time
from types import SimpleNamespace
from typing import List

import pika
import requests

from scheduler import context, queues, rankers
from scheduler.models import NormalizerTask, Organisation, PrioritizedItem, RawData

from .scheduler import Scheduler


class NormalizerScheduler(Scheduler):
    """A KAT specific implementation of a Normalizer scheduler. It extends
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
        while not self.queue.full():
            time.sleep(1)

            try:
                latest_raw_data = self.ctx.services.raw_data.get_latest_raw_data(
                    queue=f"{self.organisation.id}__raw_file_received",
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get last run boefjes [organisation.id=%s, scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue
            except (
                pika.exceptions.ConnectionClosed,
                pika.exceptions.ChannelClosed,
                pika.exceptions.ChannelClosedByBroker,
                pika.exceptions.AMQPConnectionError,
            ) as e:
                self.logger.debug(
                    "Could not connect to rabbitmq queue: %s [organisation.id=%s, scheduler_id=%s]",
                    f"{self.organisation.id}__raw_file_received",
                    self.organisation.id,
                    self.scheduler_id,
                )
                if self.stop_event.is_set():
                    raise e

                time.sleep(60)
                continue

            if latest_raw_data is None:
                self.logger.debug(
                    "No new raw data on message queue [organisation.id=%s, scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                break

            for mime_type in latest_raw_data.raw_data.mime_types:
                if mime_type.get("value", "").startswith("error/"):
                    self.logger.info(
                        "Skipping raw data with error mime type [organisation.id=%s, scheduler_id=%s]",
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

            p_items = self.create_tasks_for_raw_data(latest_raw_data.raw_data)
            if not p_items:
                continue

            # NOTE: maxsize 0 means unlimited
            while len(p_items) > (self.queue.maxsize - self.queue.qsize()) and self.queue.maxsize != 0:
                self.logger.debug(
                    "Waiting for queue to have enough space, not adding %d tasks to queue "
                    "[queue.qsize=%d, queue.maxsize=%d, organisation.id=%s, scheduler_id=%s]",
                    len(p_items),
                    self.queue.qsize(),
                    self.queue.maxsize,
                    self.organisation.id,
                    self.scheduler_id,
                )
                time.sleep(1)

            self.push_items_to_queue(p_items)
        else:
            self.logger.warning(
                "Normalizer queue is full, not populating with new tasks "
                "[queue.qsize=%d, organisation.id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

    def create_tasks_for_raw_data(self, raw_data: RawData) -> List[PrioritizedItem]:
        """Create normalizer tasks for every boefje that has been processed,
        and created raw data in Bytes.
        """
        p_items: List[PrioritizedItem] = []

        for mime_type in raw_data.mime_types:
            try:
                normalizers = self.ctx.services.katalogus.get_normalizers_by_org_id_and_type(
                    self.organisation.id,
                    mime_type.get("value"),
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get normalizers for org: %s and mime_type: %s "
                    "[boefje_meta.id=%s, organisation.id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    mime_type,
                    raw_data.boefje_meta.id,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            if normalizers is None:
                self.logger.debug(
                    "No normalizers found for mime_type: %s [mime_type=%s, organisation.id=%s, scheduler_id=%s]",
                    mime_type.get("value"),
                    mime_type.get("value"),
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            self.logger.debug(
                "Found %d normalizers for mime_type: %s "
                "[mime_type=%s, normalizers=%s, organisation.id=%s, scheduler_id=%s]",
                len(normalizers),
                mime_type.get("value"),
                mime_type.get("value"),
                [normalizer.name for normalizer in normalizers],
                self.organisation.id,
                self.scheduler_id,
            )

            for normalizer in normalizers:
                if normalizer.enabled is False:
                    self.logger.debug(
                        "Normalizer: %s is disabled for org: %s "
                        "[normalizer.id=%s, organisation.id=%s, scheduler_id=%s]",
                        normalizer.name,
                        self.organisation.name,
                        normalizer.id,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                task = NormalizerTask(
                    normalizer=normalizer,
                    raw_data=raw_data,
                )

                if self.queue.is_item_on_queue(PrioritizedItem(scheduler_id=self.scheduler_id, data=task)):
                    self.logger.debug(
                        "Normalizer task: %s is already on queue "
                        "[normalizer_id=%s, boefje_meta_id=%s, org_id=%s, scheduler_id=%s]",
                        normalizer.name,
                        normalizer.id,
                        raw_data.boefje_meta.id,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                score = self.ranker.rank(SimpleNamespace(raw_data=raw_data, task=task))
                p_items.append(PrioritizedItem(id=task.id, scheduler_id=self.scheduler_id, priority=score, data=task))

                self.logger.debug(
                    "Created normalizer task: %s for raw data: %s "
                    "[normalizer.id=%s, raw_data.id=%s, organisation.id=%s, scheduler_id=%s]",
                    normalizer.name,
                    raw_data.id,
                    normalizer.id,
                    raw_data.id,
                    self.organisation.id,
                    self.scheduler_id,
                )

        return p_items
