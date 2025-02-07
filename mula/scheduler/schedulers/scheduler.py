import abc
import random
import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from opentelemetry import trace

from scheduler import clients, context, models, storage, utils
from scheduler.schedulers.queue import PriorityQueue
from scheduler.schedulers.queue.errors import InvalidItemError, NotAllowedError, QueueEmptyError, QueueFullError
from scheduler.utils import cron, thread

tracer = trace.get_tracer(__name__)


class Scheduler(abc.ABC):
    """The Scheduler class combines the priority queue.
    The scheduler is responsible for populating the queue, and ranking tasks.

    Attributes:
        logger:
            The logger for the class
        ctx:
            Application context of shared data (e.g. configuration, external
            services connections).
        queue:
            A queue.PriorityQueue instance
        callback:
            A callback function to call when the scheduler is stopped.
        scheduler_id:
             The id of the scheduler.
        max_tries:
            The maximum number of retries for an item to be pushed to
            the queue.
        enabled:
            Whether the scheduler is enabled or not.
        _last_activity:
            The last activity of the scheduler.
        listeners:
            A dict of connector.Listener instances, used for listening to
            external events.
        lock:
            A threading.Lock instance used for locking
        stop_event_threads:
            A threading.Event object used for communicating a stop
            event across threads.
        threads:
            A dict of ThreadRunner instances, used for running processes
            concurrently.
    """

    ITEM_TYPE: Any = None

    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        queue: PriorityQueue | None = None,
        callback: Callable[..., None] | None = None,
        max_tries: int = -1,
        create_schedule: bool = False,
        auto_calculate_deadline: bool = True,
    ):
        """Initialize the Scheduler.

        Args:
            ctx:
                Application context of shared data (e.g. configuration, external
                services connections).
            scheduler_id:
                The id of the scheduler.
            queue:
                A queue.PriorityQueue instance
            callback:
                A callback function to call when the scheduler is stopped.
            max_tries:
                The maximum number of retries for an item to be pushed to
                the queue.
        """

        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.callback: Callable[[], Any] | None = callback

        # Properties
        self.scheduler_id: str = scheduler_id
        self.max_tries: int = max_tries
        self.enabled: bool = True
        self.create_schedule: bool = create_schedule
        self.auto_calculate_deadline: bool = auto_calculate_deadline
        self._last_activity: datetime | None = None

        # Queue
        self.queue = queue or PriorityQueue(
            pq_id=scheduler_id,
            maxsize=self.ctx.config.pq_maxsize,
            item_type=self.ITEM_TYPE,
            pq_store=self.ctx.datastores.pq_store,
        )

        # Listeners
        self.listeners: dict[str, clients.amqp.Listener] = {}

        # Threads
        self.lock: threading.Lock = threading.Lock()
        self.stop_event_threads: threading.Event = threading.Event()
        self.threads: list[thread.ThreadRunner] = []

    @abc.abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    def run_in_thread(
        self, name: str, target: Callable[[], Any], interval: float = 0.01, daemon: bool = False, loop: bool = True
    ) -> None:
        """Make a function run in a thread, and add it to the dict of threads.

        Args:
            name: The name of the thread.
            target: The function to run in the thread.
            interval: The interval to run the function.
            daemon: Whether the thread should be a daemon.
            loop: Whether the thread should loop.
        """
        t = utils.ThreadRunner(
            name=name, target=target, stop_event=self.stop_event_threads, interval=interval, daemon=daemon, loop=loop
        )
        t.start()

        self.threads.append(t)

    def push_items_to_queue(self, items: list[models.Task]) -> None:
        """Push multiple items to the queue.

        Args:
            items: A list of items to push to the queue.
        """
        count = 0
        for item in items:
            try:
                self.push_item_to_queue(item)
            except (NotAllowedError, QueueFullError, InvalidItemError) as exc:
                self.logger.debug(
                    "Unable to push item %s to queue %s (%s)",
                    item.id,
                    self.queue.pq_id,
                    exc,
                    item_id=item.id,
                    queue_id=self.queue.pq_id,
                    scheduler_id=self.scheduler_id,
                )
                continue
            except Exception as exc:
                self.logger.error(
                    "Unable to push item %s to queue %s",
                    item.id,
                    self.queue.pq_id,
                    item_id=item.id,
                    queue_id=self.queue.pq_id,
                    scheduler_id=self.scheduler_id,
                )
                raise exc

            count += 1

    def push_item_to_queue_with_timeout(
        self, item: models.Task, max_tries: int = 5, timeout: int = 1, create_schedule: bool = True
    ) -> None:
        """Push an item to the queue, with a timeout.

        Args:
            item: The item to push to the queue.
            timeout: The timeout in seconds.
            max_tries: The maximum number of tries. Set to -1 for infinite tries.

        Raises:
            QueueFullError: When the queue is full.
        """
        tries = 0
        while not self.is_space_on_queue() and (tries < max_tries or max_tries == -1):
            self.logger.debug(
                "Queue %s is full, waiting for space",
                queue_id=self.queue.pq_id,
                queue_qsize=self.queue.qsize(),
                scheduler_id=self.scheduler_id,
            )
            time.sleep(timeout)
            tries += 1

        if tries >= max_tries and max_tries != -1:
            raise QueueFullError()

        self.push_item_to_queue(item, create_schedule=create_schedule)

    def push_item_to_queue(self, item: models.Task, create_schedule: bool = True) -> models.Task:
        """Push a Task to the queue.

        Args:
            item: The item to push to the queue.

        Raises:
            NotAllowedError: When the scheduler is disabled.
            QueueFullError: When the queue is full.
            InvalidItemError: When the item is invalid.
        """
        if not self.is_enabled():
            self.logger.warning(
                "Scheduler is disabled, not pushing item to queue %s",
                self.queue.pq_id,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            raise NotAllowedError("Scheduler is disabled")

        try:
            if item.type is None:
                item.type = self.ITEM_TYPE.type
            item.status = models.TaskStatus.QUEUED
            item = self.queue.push(item)
        except NotAllowedError as exc:
            self.logger.warning(
                "Not allowed to push to queue %s (%s)",
                self.queue.pq_id,
                exc,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            raise exc
        except QueueFullError as exc:
            self.logger.warning(
                "Queue %s is full, not pushing new items (%s)",
                self.queue.pq_id,
                exc,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                queue_qsize=self.queue.qsize(),
                scheduler_id=self.scheduler_id,
            )
            raise exc
        except InvalidItemError as exc:
            self.logger.warning(
                "Invalid item %s",
                item.id,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                queue_qsize=self.queue.qsize(),
                scheduler_id=self.scheduler_id,
            )
            raise exc

        self.logger.debug(
            "Pushed item %s to queue %s with priority %s ",
            item.id,
            self.queue.pq_id,
            item.priority,
            item_id=item.id,
            item_hash=item.hash,
            queue_id=self.queue.pq_id,
            scheduler_id=self.scheduler_id,
        )

        item = self.post_push(item, create_schedule)

        return item

    def post_push(self, item: models.Task, create_schedule: bool = True) -> models.Task:
        """After an in item is pushed to the queue, we execute this function

        Args:
            item: The item from the priority queue.
        """
        self.last_activity = datetime.now(timezone.utc)

        if self.create_schedule is False:
            self.logger.debug(
                "Not creating schedule for item %s",
                item.id,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            return item

        scheduler_create_schedule = self.create_schedule
        if not scheduler_create_schedule:
            self.logger.debug(
                "Scheduler is not creating schedules, not creating schedule for item %s",
                item.id,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            return item

        item_create_schedule = create_schedule
        if not item_create_schedule:
            self.logger.debug(
                "Item is not creating schedules, not creating schedule for item %s",
                item.id,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            return item

        schedule_db = None
        if item.schedule_id is not None:
            schedule_db = self.ctx.datastores.schedule_store.get_schedule(item.schedule_id)
        else:
            schedule_db = self.ctx.datastores.schedule_store.get_schedule_by_hash(item.hash)

        if schedule_db is None:
            schedule = models.Schedule(scheduler_id=self.scheduler_id, hash=item.hash, data=item.data)
            schedule_db = self.ctx.datastores.schedule_store.create_schedule(schedule)

        if schedule_db is None:
            self.logger.debug(
                "No schedule found for item %s",
                item.id,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            return item

        if not schedule_db.enabled:
            self.logger.debug(
                "Schedule %s is disabled, not updating deadline",
                schedule_db.id,
                schedule_id=schedule_db.id,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            return item

        item.schedule_id = schedule_db.id

        # Determine the cron expression, either from the overridden set_cron()
        # or explicitly set.
        cron_expr = self.set_cron(item)
        if cron_expr is not None:
            schedule_db.schedule = cron_expr

        # When a Schedule does not have a schedule (cron expression), we
        # calculate the deadline when a Schedules specified a way to calculate
        # this. Otherwise we set the deadline to None make sure the Schedule
        # will not continue to be processed.
        if schedule_db.schedule is not None:
            schedule_db.deadline_at = cron.next_run(schedule_db.schedule)
        elif self.auto_calculate_deadline:
            schedule_db.deadline_at = self.calculate_deadline(item)
        else:
            schedule_db.deadline_at = None

        self.ctx.datastores.schedule_store.update_schedule(schedule_db)
        self.ctx.datastores.task_store.update_task(item)

        return item

    def pop_item_from_queue(self, filters: storage.filters.FilterRequest | None = None) -> models.Task | None:
        """Pop an item from the queue.

        Args:
            filters: Optional filters to apply when popping an item.

        Returns:
            An item from the queue

        Raises:
            NotAllowedError: When the scheduler is disabled.
            QueueEmptyError: When the queue is empty.
        """
        if not self.is_enabled():
            self.logger.warning(
                "Scheduler is disabled, not popping item from queue",
                queue_id=self.queue.pq_id,
                queue_qsize=self.queue.qsize(),
                scheduler_id=self.scheduler_id,
            )
            raise NotAllowedError("Scheduler is disabled")

        try:
            item = self.queue.pop(filters)
        except QueueEmptyError as exc:
            raise exc

        if item is not None:
            self.logger.debug(
                "Popped item %s from queue %s with priority %s",
                item.id,
                self.queue.pq_id,
                item.priority,
                item_id=item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )

            self.post_pop(item)

        return item

    def post_pop(self, item: models.Task) -> None:
        """After an item is popped from the queue, we execute this function

        Args:
            item: An item from the queue
        """
        self.last_activity = datetime.now(timezone.utc)

    def set_cron(self, task: models.Task) -> str | None:
        """Set the cron schedule for the task."""
        return None

    def calculate_deadline(self, task: models.Task) -> datetime:
        """The default deadline calculation for a task, when the
        auto_calculate_deadline attribute is set to True"""
        # We at least delay a job by the grace period
        minimum = self.ctx.config.pq_grace_period
        deadline = datetime.now(timezone.utc) + timedelta(seconds=minimum)

        # We want to delay the job by a random amount of time, in a range of 5 hours
        jitter_range_seconds = 5 * 60 * 60
        jitter = timedelta(seconds=random.uniform(0, jitter_range_seconds))  # noqa

        # Check if the adjusted time is earlier than the minimum, and
        # ensure that the adjusted time is not earlier than the deadline
        adjusted_time = deadline + jitter

        return adjusted_time

    def enable(self) -> None:
        """Enable the scheduler.

        This will start the scheduler, and start all listeners and threads.
        """
        if self.is_enabled():
            self.logger.debug("Scheduler is already enabled")
            return

        self.logger.info("Enabling scheduler: %s", self.scheduler_id, scheduler_id=self.scheduler_id)
        self.enabled = True
        self.stop_event_threads.clear()
        self.run()

        self.logger.info("Enabled scheduler: %s", self.scheduler_id, scheduler_id=self.scheduler_id)

    def disable(self) -> None:
        """Disable the scheduler.

        This will stop all listeners and threads, and clear the queue, and any
        tasks that were on the queue will be set to CANCELLED.
        """
        if not self.is_enabled():
            self.logger.warning("Scheduler already disabled: %s", self.scheduler_id, scheduler_id=self.scheduler_id)
            return

        self.logger.info("Disabling scheduler: %s", self.scheduler_id)
        self.enabled = False

        self.stop_listeners()
        self.stop_threads()
        self.queue.clear()

        # Get all tasks that were on the queue and set them to CANCELLED
        tasks, _ = self.ctx.datastores.task_store.get_tasks(
            scheduler_id=self.scheduler_id, status=models.TaskStatus.QUEUED
        )
        task_ids = [task.id for task in tasks]
        self.ctx.datastores.task_store.cancel_tasks(scheduler_id=self.scheduler_id, task_ids=task_ids)

        self.logger.info("Disabled scheduler: %s", self.scheduler_id, scheduler_id=self.scheduler_id)

    def stop(self, callback: bool = True) -> None:
        """Stop the scheduler.

        Args:
            callback: Whether to call the callback function.
        """
        self.logger.info("Stopping scheduler: %s", self.scheduler_id, scheduler_id=self.scheduler_id)

        # First, stop the listeners, when those are running in a thread and
        # they're using rabbitmq, they will block. Setting the stop event
        # will not stop the thread. We need to explicitly stop the listener.
        self.stop_listeners()
        self.stop_threads()

        if self.callback and callback:
            self.callback(self.scheduler_id)  # type: ignore [call-arg]

        self.logger.info("Stopped scheduler: %s", self.scheduler_id, scheduler_id=self.scheduler_id)

    def stop_listeners(self) -> None:
        """Stop the listeners."""
        for lst in self.listeners.copy().values():
            lst.stop()

        self.listeners = {}

    def stop_threads(self) -> None:
        """Stop the threads."""
        for t in self.threads.copy():
            t.join(5)

        self.threads = []

    def is_enabled(self) -> bool:
        """Check if the scheduler is enabled.

        Returns:
            True if the scheduler is enabled, False otherwise.
        """
        return self.enabled

    def is_space_on_queue(self) -> bool:
        """Check if there is space on the queue.

        NOTE: maxsize 0 means unlimited

        Returns:
            True if there is space on the queue, False otherwise.
        """
        if (self.queue.maxsize - self.queue.qsize()) <= 0 and self.queue.maxsize != 0:
            return False

        return True

    def is_item_on_queue_by_hash(self, item_hash: str) -> bool:
        return self.queue.is_item_on_queue_by_hash(item_hash)

    @property
    def last_activity(self) -> datetime | None:
        """Get the last activity of the scheduler."""
        with self.lock:
            return self._last_activity

    @last_activity.setter
    def last_activity(self, value: datetime) -> None:
        """Set the last activity of the scheduler."""
        with self.lock:
            self._last_activity = value

    def dict(self) -> dict[str, Any]:
        """Get a dict representation of the scheduler."""
        return {
            "id": self.scheduler_id,
            "enabled": self.enabled,
            "priority_queue": {
                "id": self.queue.pq_id,
                "item_type": self.queue.item_type.type,
                "maxsize": self.queue.maxsize,
                "qsize": self.queue.qsize(),
                "allow_replace": self.queue.allow_replace,
                "allow_updates": self.queue.allow_updates,
                "allow_priority_updates": self.queue.allow_priority_updates,
            },
            "last_activity": self.last_activity,
        }
