import time
import uuid
from types import SimpleNamespace
from typing import List

import pika
import requests

from scheduler import context, dispatchers, queues, rankers
from scheduler.models import NormalizerTask, Organisation, RawData

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
        while not self.queue.full():
            time.sleep(1)

            try:
                latest_raw_data = self.ctx.services.raw_data.get_latest_raw_data(
                    queue=f"{self.organisation.id}__raw_file_received",
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get last run boefjes [org_id=%s, scheduler_id=%s]",
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
                self.logger.warning(
                    "Could not connect to rabbitmq queue: %s [org_id=%s, scheduler_id=%s]",
                    f"{self.organisation.id}__raw_file_received",
                    self.organisation.id,
                    self.scheduler_id,
                )
                if self.stop_event.is_set():
                    raise e

                time.sleep(60)
                continue

            if latest_raw_data is None:
                self.logger.info(
                    "No latest raw data found [org_id=%s, scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                break

            p_items = self.create_tasks_for_raw_data(latest_raw_data)
            if not p_items:
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
                "Normalizer queue is full, not populating with new tasks [qsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.pq.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

    def create_tasks_for_raw_data(self, raw_data: RawData) -> List[queues.PrioritizedItem]:
        """Create normalizer tasks for every boefje that has been processed,
        and created raw data in Bytes.
        """
        p_items: List[queues.PrioritizedItem] = []

        for mime_type in raw_data.mime_types:
            try:
                normalizers = self.ctx.services.katalogus.get_normalizers_by_org_id_and_type(
                    self.organisation.id,
                    mime_type.get("value"),
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get normalizers for org: %s and mime_type: %s [boefje_meta_id=%s, org_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    mime_type,
                    raw_data.boefje_meta.id,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            if normalizers is None:
                self.logger.debug(
                    "No normalizers found for mime_type: %s [mime_type=%s, org_id=%s, scheduler_id=%s]",
                    mime_type.get("value"),
                    mime_type.get("value"),
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            self.logger.debug(
                "Found %d normalizers for mime_type: %s [mime_type=%s, normalizers=%s, org_id=%s, scheduler_id=%s]",
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
                        "Normalizer: %s is disabled for org: %s [plugin_id=%s, org_id=%s, scheduler_id=%s]",
                        normalizer.name,
                        self.organisation.name,
                        normalizer.id,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                task = NormalizerTask(
                    id=uuid.uuid4().hex,
                    normalizer=normalizer,
                    boefje_meta=raw_data.boefje_meta,
                )

                if self.queue.is_item_on_queue(task):
                    self.logger.debug(
                        "Normalizer task: %s is already on queue [normalizer_id=%s, boefje_meta_id=%s, org_id=%s, scheduler_id=%s]",
                        normalizer.name,
                        normalizer.id,
                        raw_data.boefje_meta.id,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                score = self.ranker.rank(SimpleNamespace(raw_data=raw_data, task=task))
                p_items.append(queues.PrioritizedItem(priority=score, item=task))

        return p_items
