import datetime
import time
import uuid
from types import SimpleNamespace
from typing import List

import mmh3
import pika
import requests

from scheduler import context, queues, rankers
from scheduler.models import NormalizerTask, Organisation, RawData, TaskStatus

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

            # When receiving this, it means the item on boefje queue has been
            # processed, update the status of that task.
            boefje_task_db = self.ctx.datastore.get_task_by_id(
                latest_raw_data.raw_data.boefje_meta.id,
            )
            if boefje_task_db is None:
                self.logger.warning(
                    "Could not find boefje task in database [raw_data_id=%s, org_id=%s, scheduler_id=%s]",
                    latest_raw_data.raw_data.boefje_meta.id,
                    self.organisation.id,
                    self.scheduler_id,
                )

            # Check status of the job and update status of boefje tasks, and
            # stop creating normalizer tasks.
            if boefje_task_db is not None:
                status = TaskStatus.COMPLETED

                for mime_type in latest_raw_data.raw_data.mime_types:
                    if mime_type.get("value", "").startswith("error/"):
                        status = TaskStatus.FAILED
                        boefje_task_db.status = status

                        self.ctx.datastore.update_task(boefje_task_db)
                        return

                boefje_task_db.status = status
                self.ctx.datastore.update_task(boefje_task_db)

            p_items = self.create_tasks_for_raw_data(latest_raw_data.raw_data)
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

            self.push_items_to_queue(p_items)
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

    def update_normalizer_task_status(self):
        try:
            latest_normalizer_meta = self.ctx.services.normalizer_meta.get_latest_normalizer_meta(
                queue=f"{self.organisation.id}__normalizer_meta_received",
            )
        except (
            pika.exceptions.ConnectionClosed,
            pika.exceptions.ChannelClosed,
            pika.exceptions.ChannelClosedByBroker,
            pika.exceptions.AMQPConnectionError,
        ) as e:
            self.logger.warning(
                "Could not connect to rabbitmq queue: %s [org_id=%s, scheduler_id=%s]",
                f"{self.organisation.id}__normalizer_meta_received",
                self.organisation.id,
                self.scheduler_id,
            )
            if self.stop_event.is_set():
                raise e

            time.sleep(60)
            return

        if latest_normalizer_meta is None:
            self.logger.debug(
                "No normalizer meta found on queue: %s [org_id=%s, scheduler_id=%s]",
                f"{self.organisation.id}__normalizer_meta_received",
                self.organisation.id,
                self.scheduler_id,
            )
            time.sleep(60)
            return

        normalizer_task_db = self.ctx.datastore.get_task_by_id(
            latest_normalizer_meta.normalizer_meta.id,
        )
        if normalizer_task_db is None:
            self.logger.warning(
                "Could not find normalizer task in database [normalizer_meta_id=%s, org_id=%s, scheduler_id=%s]",
                latest_normalizer_meta.normalizer_meta.id,
                self.organisation.id,
                self.scheduler_id,
            )
            return

        normalizer_task_db.status = TaskStatus.COMPLETED
        self.ctx.datastore.update_task(normalizer_task_db)

    def run(self) -> None:
        super().run()

        self.run_in_thread(
            name="update_normalizer_task_status",
            func=self.update_normalizer_task_status,
        )
