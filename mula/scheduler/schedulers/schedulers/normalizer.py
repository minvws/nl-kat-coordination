import uuid
from concurrent import futures
from types import SimpleNamespace
from typing import Any

import structlog
from opentelemetry import trace

from scheduler import clients, context, models, rankers
from scheduler.clients.errors import ExternalServiceError
from scheduler.connectors.errors import ExternalServiceError
from scheduler.schedulers import Scheduler

from .scheduler import Scheduler

tracer = trace.get_tracer(__name__)


class NormalizerScheduler(Scheduler):
    """Scheduler implementation for the creation of NormalizerTask models.

    Attributes:
        ranker: The ranker to calculate the priority of a task.
    """

    ITEM_TYPE: Any = models.NormalizerTask

    def __init__(self, ctx: context.AppContext):
        """Initializes the NormalizerScheduler.

        Args:
            ctx (context.AppContext): Application context of shared data (e.g.
                configuration, external services connections).
        """
        self.scheduler_id = "normalizer"
        self.ranker = rankers.NormalizerRanker(ctx=self.ctx)

        super().__init__(ctx=ctx, queue=self.queue, scheduler_id=self.scheduler_id, create_schedule=False)

    def run(self) -> None:
        """The run method is called when the scheduler is started. It will
        start the listeners and the scheduling loops in separate threads. It
        is mainly tasked with populating the queue with tasks.

        * Raw data listener: This listener will listen to the raw file received
        messaging queue. When a new raw file is received, it will create a task
        for each normalizer that is registered for the mime type of the raw
        file.
        """
        listener = clients.RawData(
            dsn=str(self.ctx.config.host_raw_data),
            queue="raw_file_received",
            func=self.push_tasks_for_received_raw_data,
            prefetch_count=self.ctx.config.rabbitmq_prefetch_count,
        )

        self.listeners["raw_data"] = listener

        self.run_in_thread(
            name=f"NormalizerScheduler-{self.scheduler_id}-raw_file",
            target=self.listeners["raw_data"].listen,
            loop=False,
        )

        self.logger.info(
            "Normalizer scheduler started", scheduler_id=self.scheduler_id, item_type=self.queue.item_type.__name__
        )

    @tracer.start_as_current_span("normalizer_push_task_for_received_raw_data")
    def push_tasks_for_received_raw_data(self, body: bytes) -> None:
        """Create tasks for the received raw data.

        Args:
            latest_raw_data: A `RawData` object that was received from the
            message queue.
        """
        # Convert body into a RawDataReceivedEvent
        latest_raw_data = models.RawDataReceivedEvent.model_validate_json(body)

        self.logger.debug(
            "Received raw data %s",
            latest_raw_data.raw_data.id,
            raw_data_id=latest_raw_data.raw_data.id,
            scheduler_id=self.scheduler_id,
        )

        # Check if the raw data doesn't contain an error mime-type,
        # we don't need to create normalizers when the raw data returned
        # an error.
        for mime_type in latest_raw_data.raw_data.mime_types:
            if mime_type.get("value", "").startswith("error/"):
                self.logger.debug(
                    "Skipping raw data %s with error mime type",
                    latest_raw_data.raw_data.id,
                    mime_type=mime_type.get("value"),
                    raw_data_id=latest_raw_data.raw_data.id,
                )
                return

        # Get all normalizers for the mime types of the raw data
        normalizers: dict[str, models.Plugin] = {}
        for mime_type in latest_raw_data.raw_data.mime_types:
            normalizers_by_mime_type: list[models.Plugin] = self.get_normalizers_for_mime_type(
                mime_type.get("value"), latest_raw_data.organisation
            )

            for normalizer in normalizers_by_mime_type:
                normalizers[normalizer.id] = normalizer

        if not normalizers:
            self.logger.debug(
                "No normalizers found for raw data %s",
                latest_raw_data.raw_data.id,
                raw_data_id=latest_raw_data.raw_data.id,
                scheduler_id=self.scheduler_id,
            )

        with futures.ThreadPoolExecutor(
            thread_name_prefix=f"NormalizerScheduler-TPE-{self.scheduler_id}-raw_data"
        ) as executor:
            for normalizer in normalizers.values():
                if not self.has_normalizer_permission_to_run(normalizer):
                    self.logger.debug(
                        "Normalizer is not allowed to run: %s",
                        normalizer.id,
                        normalizer_id=normalizer.id,
                        scheduler_id=self.scheduler_id,
                    )
                    continue

                normalizer_task = models.NormalizerTask(
                    normalizer=models.Normalizer.model_validate(normalizer.model_dump()),
                    raw_data=latest_raw_data.raw_data,
                )

                task = models.Task(
                    id=normalizer_task.id,
                    scheduler_id=self.scheduler_id,
                    type=self.ITEM_TYPE.type,
                    hash=normalizer_task.hash,
                    data=normalizer_task.model_dump(),
                )

                executor.submit(self.push_task, task, self.push_tasks_for_received_raw_data.__name__)

    @tracer.start_as_current_span("normalizer_push_task")
    def push_task(self, task: models.Task, caller: str = "") -> None:
        """Given a normalizer and raw data, create a task and push it to the
        queue.

        Args:
            normalizer: The normalizer to create a task for.
            raw_data: The raw data to create a task for.
            caller: The name of the function that called this function, used for logging.
        """
        normalizer_task = models.NormalizerTask.model_validate(task.data)

        plugin = self.ctx.services.katalogus.get_plugin_by_id_and_org_id(
            normalizer_task.normalizer.id, task.organisation
        )
        if not self.has_normalizer_permission_to_run(plugin):
            self.logger.debug(
                "Task is not allowed to run: %s",
                normalizer_task.id,
                task_id=normalizer_task.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )
            return

        if self.has_normalizer_task_started_running(normalizer_task):
            self.logger.debug(
                "Task is still running: %s",
                normalizer_task.id,
                task_id=normalizer_task.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )
            return

        if self.is_item_on_queue_by_hash(normalizer_task.hash):
            self.logger.debug(
                "Task is already on queue: %s",
                normalizer_task.id,
                task_id=normalizer_task.id,
                scheduler_id=self.scheduler_id,
                caller=caller,
            )
            return

        task.priority = self.ranker.rank(SimpleNamespace(raw_data=normalizer_task.raw_data, task=normalizer_task))

        self.push_item_to_queue_with_timeout(task, self.max_tries)

        self.logger.info(
            "Created normalizer task",
            task_id=task.id,
            task_hash=task.hash,
            normalizer_id=normalizer_task.normalizer.id,
            raw_data_id=normalizer_task.raw_data.id,
            scheduler_id=self.scheduler_id,
            caller=caller,
        )

    def push_item_to_queue(self, item: models.Task) -> models.Task:
        """Some normalizer scheduler specific logic before pushing the item to the
        queue."""
        normalizer_task = models.NormalizerTask.model_validate(item.data)

        # Check if id's are unique and correctly set. Same id's are necessary
        # for the task runner.
        if item.id != normalizer_task.id or self.ctx.datastores.task_store.get_task(item.id):
            new_id = uuid.uuid4()
            normalizer_task.id = new_id
            item.id = new_id
            item.data = normalizer_task.model_dump()

        return super().push_item_to_queue(item)

    @tracer.start_as_current_span("normalizer_has_normalizer_permission_to_run")
    def has_normalizer_permission_to_run(self, normalizer: models.Plugin) -> bool:
        """Check if the task is allowed to run.

        Args:
            normalizer: The normalizer to check.

        Returns:
            True if the task is allowed to run, False otherwise.
        """
        if not normalizer.enabled:
            self.logger.debug(
                "Normalizer: %s is disabled", normalizer.id, normalizer_id=normalizer.id, scheduler_id=self.scheduler_id
            )
            return False

        return True

    @tracer.start_as_current_span("normalizer_has_normalizer_task_started_running")
    def has_normalizer_task_started_running(self, task: models.NormalizerTask) -> bool:
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
            self.logger.error(
                "Could not get latest task by hash: %s",
                task.hash,
                task_id=task.id,
                scheduler_id=self.scheduler_id,
                exc_info=exc_db,
            )
            raise exc_db

        # Is task still running according to the datastore?
        if task_db is not None and task_db.status not in [models.TaskStatus.COMPLETED, models.TaskStatus.FAILED]:
            self.logger.debug(
                "Task is still running, according to the datastore",
                task_id=task_db.id,
                task_hash=task.hash,
                scheduler_id=self.scheduler_id,
            )
            return True

        return False

    def get_normalizers_for_mime_type(self, mime_type: str, organisation: str) -> list[models.Plugin]:
        """Get available normalizers for a given mime type.

        Args:
            mime_type : The mime type to get normalizers for.

        Returns:
            A list of Plugins of type normalizer for the given mime type.
        """
        try:
            normalizers = self.ctx.services.katalogus.get_normalizers_by_org_id_and_type(organisation, mime_type)
        except ExternalServiceError:
            self.logger.warning(
                "Could not get normalizers for mime_type: %s [mime_type=%s, organisation_id=%s, scheduler_id=%s]",
                mime_type,
                mime_type,
                organisation,
                self.scheduler_id,
            )
            return []

        if normalizers is None:
            self.logger.debug(
                "No normalizer found for mime_type: %s", mime_type, mime_type=mime_type, scheduler_id=self.scheduler_id
            )
            return []

        self.logger.debug(
            "Found %d normalizers for mime_type: %s",
            len(normalizers),
            mime_type,
            mime_type=mime_type,
            normalizers=[normalizer.id for normalizer in normalizers],
            scheduler_id=self.scheduler_id,
        )

        return normalizers
