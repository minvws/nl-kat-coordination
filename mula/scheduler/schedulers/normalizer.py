import logging
from concurrent import futures
from types import SimpleNamespace
from typing import Callable, Dict, List, Optional

import requests

from scheduler import context, queues, rankers
from scheduler.connectors import listeners
from scheduler.models import Normalizer, NormalizerTask, Organisation, Plugin, PrioritizedItem, RawData, TaskStatus

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
        callback: Optional[Callable[..., None]] = None,
        populate_queue_enabled: bool = True,
    ):
        self.logger = logging.getLogger(__name__)
        self.organisation: Organisation = organisation

        super().__init__(
            ctx=ctx,
            scheduler_id=scheduler_id,
            queue=queue,
            ranker=ranker,
            callback=callback,
            populate_queue_enabled=populate_queue_enabled,
        )

        self.initialize_listeners()

    def run(self) -> None:
        self.run_in_thread(
            name=f"scheduler-{self.scheduler_id}-raw_file",
            target=self.listeners["raw_data"].listen,
            loop=False,
        )

    def initialize_listeners(self) -> None:
        listener = listeners.RawData(
            dsn=self.ctx.config.host_raw_data,
            queue=f"{self.organisation.id}__raw_file_received",
            func=self.push_tasks_for_received_raw_data,
            prefetch_count=self.ctx.config.queue_prefetch_count,
        )

        self.listeners["raw_data"] = listener

    def push_tasks_for_received_raw_data(self, latest_raw_data: RawData) -> None:
        """Create tasks for the received raw data.

        Args:
            latest_raw_data: A `RawData` object that was received from the
            message queue.
        """
        self.logger.debug(
            "Received new raw data from message queue [raw_data.id=%s, organisation.id=%s, scheduler_id=%s]",
            latest_raw_data.raw_data.id,
            self.organisation.id,
            self.scheduler_id,
        )

        # Check if the raw data doesn't contain an error mime-type,
        # we don't need to create normalizers when the raw data returned
        # an error.
        for mime_type in latest_raw_data.raw_data.mime_types:
            if mime_type.get("value", "").startswith("error/"):
                self.logger.warning(
                    "Skipping raw data with error mime type [raw_data.id=%s ,organisation.id=%s, scheduler_id=%s]",
                    latest_raw_data.raw_data.id,
                    self.organisation.id,
                    self.scheduler_id,
                )
                return

        # Get all normalizers for the mime types of the raw data
        normalizers: Dict[str, Normalizer] = {}
        for mime_type in latest_raw_data.raw_data.mime_types:
            normalizers_by_mime_type: List[Normalizer] = self.get_normalizers_for_mime_type(mime_type.get("value"))

            for normalizer in normalizers_by_mime_type:
                normalizers[normalizer.id] = normalizer

        if not normalizers:
            self.logger.debug(
                "No normalizers found for raw data [raw_data.id=%s, organisation.id=%s, scheduler_id=%s]",
                latest_raw_data.raw_data.id,
                self.organisation.id,
                self.scheduler_id,
            )

        with futures.ThreadPoolExecutor() as executor:
            for normalizer in normalizers.values():
                executor.submit(
                    self.push_task,
                    normalizer,
                    latest_raw_data.raw_data,
                    self.push_tasks_for_received_raw_data.__name__,
                )

    def push_task(self, normalizer: Normalizer, raw_data: RawData, caller: str = "") -> None:
        """Given a normalizer and raw data, create a task and push it to the
        queue.

        Args:
            normalizer: The normalizer to create a task for.
            raw_data: The raw data to create a task for.
            caller: The name of the function that called this function.
        """
        task = NormalizerTask(
            normalizer=normalizer,
            raw_data=raw_data,
        )

        if not self.is_task_allowed_to_run(normalizer):
            self.logger.debug(
                "Task is not allowed to run: %s [organisation.id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
            )
            return

        try:
            if self.is_task_running(task):
                self.logger.debug(
                    "Task is already running: %s [organisation.id=%s, scheduler_id=%s, caller=%s]",
                    task,
                    self.organisation.id,
                    self.scheduler_id,
                    caller,
                )
                return
        except Exception:
            self.logger.warning(
                "Could not check if task is running: %s [organisation.id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
            )
            return

        if self.is_item_on_queue_by_hash(task.hash):
            self.logger.debug(
                "Normalizer task is already on queue: %s [organisation.id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
            )
            return

        score = self.ranker.rank(
            SimpleNamespace(
                raw_data=raw_data,
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

        try:
            self.push_item_to_queue_with_timeout(p_item, self.max_tries)
        except queues.QueueFullError:
            self.logger.warning(
                "Could not add task to queue, queue was full: %s "
                "[queue.qsize=%d, queue.maxsize=%d, organisation.id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.queue.qsize(),
                self.queue.maxsize,
                self.organisation.id,
                self.scheduler_id,
                caller,
            )
            return

        self.logger.info(
            "Created normalizer task: %s for raw data: %s "
            "[normalizer.id=%s, raw_data.id=%s, organisation.id=%s, scheduler_id=%s, caller=%s]",
            task,
            raw_data.id,
            normalizer.id,
            raw_data.id,
            self.organisation.id,
            self.scheduler_id,
            caller,
        )

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
