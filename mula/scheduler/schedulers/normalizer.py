import logging
from concurrent import futures
from types import SimpleNamespace
from typing import Callable, Dict, List, Optional

import requests
from opentelemetry import trace

from scheduler import context, queues, rankers
from scheduler.connectors import listeners
from scheduler.models import Normalizer, NormalizerTask, Organisation, Plugin, PrioritizedItem, RawData, TaskStatus

from .scheduler import Scheduler

tracer = trace.get_tracer(__name__)


class NormalizerScheduler(Scheduler):
    """A KAT specific implementation of a Normalizer scheduler. It extends
    the `Scheduler` class by adding a `organisation` attribute.

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

        self.queue = queue or queues.NormalizerPriorityQueue(
            pq_id=scheduler_id,
            maxsize=ctx.config.pq_maxsize,
            item_type=NormalizerTask,
            allow_priority_updates=True,
            pq_store=ctx.datastores.pq_store,
        )

        super().__init__(
            ctx=ctx,
            queue=self.queue,
            scheduler_id=scheduler_id,
            callback=callback,
        )

        self.ranker = rankers.NormalizerRanker(
            ctx=self.ctx,
        )

    def run(self) -> None:
        """The run method is called when the scheduler is started. It will
        start the listeners and the scheduling loops in separate threads. It
        is mainly tasked with populating the queue with tasks.

        * Raw data listener: This listener will listen to the raw file received
        messaging queue. When a new raw file is received, it will create a task
        for each normalizer that is registered for the mime type of the raw
        file.
        """
        listener = listeners.RawData(
            dsn=str(self.ctx.config.host_raw_data),
            queue=f"{self.organisation.id}__raw_file_received",
            func=self.push_tasks_for_received_raw_data,
            prefetch_count=self.ctx.config.rabbitmq_prefetch_count,
        )

        self.listeners["raw_data"] = listener

        self.run_in_thread(
            name=f"scheduler-{self.scheduler_id}-raw_file",
            target=self.listeners["raw_data"].listen,
            loop=False,
        )

    @tracer.start_as_current_span("normalizer_push_task_for_received_raw_data")
    def push_tasks_for_received_raw_data(self, latest_raw_data: RawData) -> None:
        """Create tasks for the received raw data.

        Args:
            latest_raw_data: A `RawData` object that was received from the
            message queue.
        """
        self.logger.debug(
            "Received new raw data from message queue [raw_data_id=%s, organisation_id=%s, scheduler_id=%s]",
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
                    "Skipping raw data with error mime type [raw_data_id=%s, organisation_id=%s, scheduler_id=%s]",
                    latest_raw_data.raw_data.id,
                    self.organisation.id,
                    self.scheduler_id,
                )
                return

        # Get all normalizers for the mime types of the raw data
        normalizers: Dict[str, Normalizer] = {}
        for mime_type in latest_raw_data.raw_data.mime_types:
            normalizers_by_mime_type: List[Plugin] = self.get_normalizers_for_mime_type(mime_type.get("value"))

            for normalizer in normalizers_by_mime_type:
                normalizers[normalizer.id] = normalizer

        if not normalizers:
            self.logger.debug(
                "No normalizers found for raw data [raw_data_id=%s, organisation_id=%s, scheduler_id=%s]",
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

    @tracer.start_as_current_span("normalizer_push_task")
    def push_task(self, normalizer: Plugin, raw_data: RawData, caller: str = "") -> None:
        """Given a normalizer and raw data, create a task and push it to the
        queue.

        Args:
            normalizer: The normalizer to create a task for.
            raw_data: The raw data to create a task for.
            caller: The name of the function that called this function, used for logging.
        """
        task = NormalizerTask(
            normalizer=Normalizer(id=normalizer.id),
            raw_data=raw_data,
        )

        if not self.is_task_allowed_to_run(normalizer):
            self.logger.debug(
                "Task is not allowed to run: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
            )
            return

        try:
            if self.is_task_running(task):
                self.logger.debug(
                    "Task is already running: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                    task,
                    self.organisation.id,
                    self.scheduler_id,
                    caller,
                )
                return
        except Exception:
            self.logger.warning(
                "Could not check if task is running: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
                task,
                self.organisation.id,
                self.scheduler_id,
                caller,
            )
            return

        if self.is_item_on_queue_by_hash(task.hash):
            self.logger.debug(
                "Normalizer task is already on queue: %s [organisation_id=%s, scheduler_id=%s, caller=%s]",
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
            "Created normalizer task: %s for raw data: %s "
            "[normalizer_id=%s, raw_data_id=%s, organisation_id=%s, scheduler_id=%s, caller=%s]",
            task,
            raw_data.id,
            normalizer.id,
            raw_data.id,
            self.organisation.id,
            self.scheduler_id,
            caller,
        )

    def get_normalizers_for_mime_type(self, mime_type: str) -> List[Plugin]:
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
                "Could not get normalizers for mime_type: %s [mime_type=%s, organisation_id=%s, scheduler_id=%s]",
                mime_type,
                mime_type,
                self.organisation.id,
                self.scheduler_id,
            )

            return []

        if normalizers is None:
            self.logger.debug(
                "No normalizer found for mime_type: %s [mime_type=%s, organisation_id=%s, scheduler_id=%s]",
                mime_type,
                mime_type,
                self.organisation.id,
                self.scheduler_id,
            )
            return []

        self.logger.debug(
            "Found %d normalizers for mime_type: %s "
            "[mime_type=%s, normalizers=%s, organisation_id=%s, scheduler_id=%s]",
            len(normalizers),
            mime_type,
            mime_type,
            [normalizer.id for normalizer in normalizers],
            self.organisation.id,
            self.scheduler_id,
        )

        return normalizers

    @tracer.start_as_current_span("normalizer_is_task_allowed_to_run")
    def is_task_allowed_to_run(self, normalizer: Plugin) -> bool:
        """Check if the task is allowed to run.

        Args:
            normalizer: The normalizer to check.

        Returns:
            True if the task is allowed to run, False otherwise.
        """
        if not normalizer.enabled:
            self.logger.debug(
                "Normalizer: %s is disabled [normalizer_id= %s, organisation_id=%s, scheduler_id=%s]",
                normalizer.id,
                normalizer.id,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        return True

    @tracer.start_as_current_span("normalizer_is_task_running")
    def is_task_running(self, task: NormalizerTask) -> bool:
        """Check if the same task is already running.

        Args:
            task: The NormalizerTask to check.

        Returns:
            True if the task is still running, False otherwise.
        """
        # Get the last tasks that have run or are running for the hash
        # of this particular NormalizerTask.
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

        # Is task still running according to the datastore?
        if task_db is not None and task_db.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            self.logger.debug(
                "Task is still running, according to the datastore "
                "[task_id=%s, task_hash=%s, organisation_id=%s, scheduler_id=%s]",
                task_db.id,
                task.hash,
                self.organisation.id,
                self.scheduler_id,
            )
            return True

        return False
