import logging
import time
from types import SimpleNamespace
from typing import List

import pika
import requests

from scheduler import context, queues, rankers
from scheduler.models import Normalizer, NormalizerTask, Organisation, Plugin, PrioritizedItem, TaskStatus

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
        """Populate the PriorityQueue"""
        self.push_tasks_for_received_raw_file()

    def push_tasks_for_received_raw_file(self) -> None:
        while not self.queue.full():
            time.sleep(1)

            latest_raw_data = None
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

            # Stop the loop when we've processed everything from the
            # messaging queue, so we can continue to the next step.
            if latest_raw_data is None:
                self.logger.debug(
                    "No new raw data on message queue [organisation.id=%s, scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                return

            self.logger.debug(
                "Received new raw data from message queue [raw_data.id=%s, organisation.id=%s, scheduler_id=%s]",
                latest_raw_data.raw_data.id,
                self.organisation.id,
                self.scheduler_id,
            )

            # First check if the raw data doesn't contain an error.
            for mime_type in latest_raw_data.raw_data.mime_types:
                if mime_type.get("value", "").startswith("error/"):
                    self.logger.warning(
                        "Skipping raw data with error mime type [raw_data.id=%s ,organisation.id=%s, scheduler_id=%s]",
                        latest_raw_data.raw_data.id,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    return

            normalizers = []
            for mime_type in latest_raw_data.raw_data.mime_types:
                normalizers_by_mime_type = self.get_normalizers_for_mime_type(mime_type.get("value"))
                if normalizers_by_mime_type is None or len(normalizers_by_mime_type) == 0:
                    continue

                normalizers.extend(normalizers_by_mime_type)

            if normalizers is None or len(normalizers) == 0:
                self.logger.debug(
                    "No normalizers found for raw data [raw_data.id=%s, organisation.id=%s, scheduler_id=%s]",
                    latest_raw_data.raw_data.id,
                    self.organisation.id,
                    self.scheduler_id,
                )

            for normalizer in normalizers:
                task = NormalizerTask(
                    normalizer=normalizer,
                    raw_data=latest_raw_data.raw_data,
                )

                if not self.is_task_allowed_to_run(normalizer):
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

                if self.queue.is_item_on_queue_by_hash(task.hash):
                    self.logger.debug(
                        "Normalizer task is already on queue: %s [organisation.id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                score = self.ranker.rank(
                    SimpleNamespace(
                        raw_data=latest_raw_data.raw_data,
                        task=task,
                    ),
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
                    "Created normalizer task: %s for raw data: %s "
                    "[normalizer.id=%s, raw_data.id=%s, organisation.id=%s, scheduler_id=%s]",
                    normalizer.id,
                    latest_raw_data.raw_data.id,
                    normalizer.id,
                    latest_raw_data.raw_data.id,
                    self.organisation.id,
                    self.scheduler_id,
                )
                self.push_item_to_queue(p_item)
        else:
            self.logger.warning(
                "Normalizer queue is full, not populating with new tasks "
                "[queue.qsize=%d, queue.maxsize=%d, organisation.id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

    def get_normalizers_for_mime_type(self, mime_type: str) -> List[Normalizer]:
        """Get available normalizers for a given mime type.

        Args:
            mime_type : The mime type to get normalizers for.

        Returns:
            A list of normalizers for the given mime type.
        """
        try:
            normalizers = self.ctx.services.katalogus.get_normalizers_by_org_id_and_type(
                self.organisation.id,
                mime_type,
            )
        except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
            self.logger.warning(
                "Could not get normalizers for mime_type: %s [mime_type=%s, organisation.id=%s, scheduler_id=%s]",
                mime_type,
                mime_type,
                self.organisation.id,
                self.scheduler_id,
            )

            return []

        if normalizers is None:
            self.logger.debug(
                "No normalizer found for mime_type: %s [mime_type=%s, organisation.id=%s, scheduler_id=%s]",
                mime_type,
                mime_type,
                self.organisation.id,
                self.scheduler_id,
            )
            return []

        self.logger.debug(
            "Found %d normalizers for mime_type: %s "
            "[mime_type=%s, normalizers=%s, organisation.id=%s, scheduler_id=%s]",
            len(normalizers),
            mime_type,
            mime_type,
            [normalizer.name for normalizer in normalizers],
            self.organisation.id,
            self.scheduler_id,
        )

        return normalizers

    def is_task_allowed_to_run(self, normalizer: Plugin) -> bool:
        """Check if the task is allowed to run.

        Args:
            task: The task to check.

        Returns:
            True if the task is allowed to run, False otherwise.
        """
        if not normalizer.enabled:
            self.logger.debug(
                "Normalizer: %s is disabled [normalizer.id= %s, organisation.id=%s, scheduler_id=%s]",
                normalizer.id,
                normalizer.id,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        return True

    def is_task_running(self, task: NormalizerTask) -> bool:
        """Check if the same task is already running.

        Args:
            task: The task to check.

        Returns:
            True if the task is already running, False otherwise.
        """
        # Get the last tasks that have run or are running for the hash
        # of this particular NormalizerTask.
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

        # Is task still running according to the datastore?
        if task_db is not None and task_db.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            self.logger.debug(
                "Task is still running, according to the datastore "
                "[task.id=%s, task.hash=%s, organisation.id=%s, scheduler_id=%s]",
                task_db.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            return True

        return False

    def is_space_on_queue(self) -> bool:
        """Check if there is space on the queue.

        NOTE: maxsize 0 means unlimited
        """
        if (self.queue.maxsize - self.queue.qsize()) <= 0 and self.queue.maxsize != 0:
            return False

        return True
