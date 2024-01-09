import abc
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

import structlog

from scheduler import connectors, context, models, queues, rankers, storage, utils
from scheduler.utils import thread


class Scheduler(abc.ABC):
    """The Scheduler class combines the priority queue.
    The scheduler is responsible for populating the queue, and ranking tasks.

    Attributes:
        logger:
            The logger for the class
        ctx:
            Application context of shared data (e.g. configuration, external
            services connections).
        enabled:
            Whether the scheduler is enabled or not.
        scheduler_id:
            The id of the scheduler.
        queue:
            A queues.PriorityQueue instance
        threads:
            A dict of ThreadRunner instances, used for running processes
            concurrently.
        stop_event: A threading.Event object used for communicating a stop
            event across threads.
        listeners:
            A dict of connector.Listener instances, used for listening to
            external events.
    """

    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        queue: queues.PriorityQueue,
        callback: Optional[Callable[..., None]] = None,
        max_tries: int = -1,
    ):
        """Initialize the Scheduler.

        Args:
            ctx:
                Application context of shared data (e.g. configuration, external
                services connections).
            scheduler_id:
                The id of the scheduler.
            queue:
                A queues.PriorityQueue instance
            ranker:
                A rankers.Ranker instance.
            max_tries:
                The maximum number of retries for a task to be pushed to
                the queue.
        """

        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.enabled: bool = True
        self.scheduler_id: str = scheduler_id
        self.queue: queues.PriorityQueue = queue
        self.max_tries: int = max_tries
        self.callback: Optional[Callable[[], Any]] = callback
        self._last_activity: Optional[datetime] = None
        self.job_ranker = rankers.JobDeadlineRanker(ctx=self.ctx)

        # Listeners
        self.listeners: Dict[str, connectors.listeners.Listener] = {}

        # Threads
        self.lock: threading.Lock = threading.Lock()
        self.stop_event_threads: threading.Event = threading.Event()
        self.threads: List[thread.ThreadRunner] = []

    @abc.abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    def post_push(self, p_item: models.PrioritizedItem) -> None:
        """When a boefje task is being added to the queue. We
        persist a task to the datastore with the status QUEUED.

        Args:
            p_item: The prioritized item from the priority queue.
        """
        # Set last activity of scheduler
        self.last_activity = datetime.now(timezone.utc)

        # Create Job
        #
        # Do we have a job for this task?
        job_db = self.ctx.datastores.job_store.get_job_by_hash(p_item.hash)
        if job_db is None:
            job_db = self.ctx.datastores.job_store.create_job(
                models.Job(
                    scheduler_id=self.scheduler_id,
                    p_item=p_item,
                    deadline_at=datetime.now(timezone.utc) + timedelta(seconds=self.ctx.config.pq_grace_period),
                    created_at=datetime.now(timezone.utc),
                    modified_at=datetime.now(timezone.utc),
                )
            )

        # FIXME: what if we want to explicitly disable a job, e.g. we just want
        # to have a one-off? We disable a job for the boefje scheduler when a
        # ooi is deleted, or when a boefje is disabled.

        # Was job disabled? If so, re-enable it. When we get here all checks
        # have been done for the p_item, so we can assume that the job is
        # can be marked for rescheduling.
        if not job_db.enabled:
            job_db.enabled = True
            self.ctx.datastores.job_store.update_job(job_db)

        # Create Task
        #
        # NOTE: we set the id of the task the same as the p_item, for easier
        # lookup.
        task = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler_id,
            type=self.queue.item_type.type,
            p_item=p_item,
            status=models.TaskStatus.QUEUED,
            job_id=job_db.id,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        task_db = self.ctx.datastores.task_store.get_task_by_id(str(p_item.id))
        if task_db is not None:
            self.ctx.datastores.task_store.update_task(task)
            return

        self.ctx.datastores.task_store.create_task(task)

    def post_pop(self, p_item: models.PrioritizedItem) -> None:
        """When a boefje task is being removed from the queue. We
        persist a task to the datastore with the status RUNNING

        Args:
            p_item: The prioritized item from the priority queue.
        """
        # Update Task
        task = self.ctx.datastores.task_store.get_task_by_id(str(p_item.id))
        if task is None:
            self.logger.warning(
                "PrioritizedItem %s popped from %s, task %s not found in datastore, could not update task status",
                p_item.id,
                self.queue.pq_id,
                p_item.data.get("id"),
                p_item_id=p_item.id,
                task_id=p_item.data.get("id"),
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            return

        task.status = models.TaskStatus.DISPATCHED
        self.ctx.datastores.task_store.update_task(task)

        # Set last activity of scheduler
        self.last_activity = datetime.now(timezone.utc)

    def pop_item_from_queue(
        self, filters: Optional[storage.filters.FilterRequest] = None
    ) -> Optional[models.PrioritizedItem]:
        """Pop an item from the queue.

        Args:
            filters: A FilterRequest instance to filter the
            prioritized items from the queue.

        Returns:
            A PrioritizedItem instance.
        """
        if not self.is_enabled():
            self.logger.warning(
                "Scheduler is disabled, not popping item from queue",
                queue_id=self.queue.pq_id,
                queue_qsize=self.queue.qsize(),
                scheduler_id=self.scheduler_id,
            )
            raise queues.errors.NotAllowedError("Scheduler is disabled")

        try:
            p_item = self.queue.pop(filters)
        except queues.QueueEmptyError as exc:
            raise exc

        if p_item is not None:
            self.logger.debug(
                "Popped item %s from queue %s with priority %s",
                p_item.id,
                self.queue.pq_id,
                p_item.priority,
                p_item_id=p_item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )

            self.post_pop(p_item)

        return p_item

    def push_item_to_queue(self, p_item: models.PrioritizedItem) -> None:
        """Push a PrioritizedItem to the queue.

        Args:
            p_item: The PrioritizedItem to push to the queue.
        """
        if not self.is_enabled():
            self.logger.warning(
                "Scheduler is disabled, not pushing item to queue %s",
                self.queue.pq_id,
                p_item_id=p_item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            raise queues.errors.NotAllowedError("Scheduler is disabled")

        try:
            self.queue.push(p_item)
        except queues.errors.NotAllowedError as exc:
            self.logger.warning(
                "Not allowed to push to queue %s",
                self.queue.pq_id,
                p_item_id=p_item.id,
                queue_id=self.queue.pq_id,
                scheduler_id=self.scheduler_id,
            )
            raise exc
        except queues.errors.QueueFullError as exc:
            self.logger.warning(
                "Queue %s is full, not pushing new items",
                self.queue.pq_id,
                p_item_id=p_item.id,
                queue_id=self.queue.pq_id,
                queue_qsize=self.queue.qsize(),
                scheduler_id=self.scheduler_id,
            )
            raise exc
        except queues.errors.InvalidPrioritizedItemError as exc:
            self.logger.warning(
                "Invalid prioritized item %s",
                p_item.id,
                p_item_id=p_item.id,
                queue_id=self.queue.pq_id,
                queue_qsize=self.queue.qsize(),
                scheduler_id=self.scheduler_id,
            )
            raise exc

        self.logger.debug(
            "Pushed item %s to queue %s with priority %s ",
            p_item.id,
            self.queue.pq_id,
            p_item.priority,
            p_item_id=p_item.id,
            queue_id=self.queue.pq_id,
            scheduler_id=self.scheduler_id,
        )

        self.post_push(p_item)

    def push_items_to_queue(self, p_items: List[models.PrioritizedItem]) -> None:
        """Push multiple PrioritizedItems to the queue.

        Args:
            p_items: The list PrioritzedItem to add to the queue.
        """
        count = 0
        for p_item in p_items:
            try:
                self.push_item_to_queue(p_item)
            except (
                queues.errors.NotAllowedError,
                queues.errors.QueueFullError,
                queues.errors.InvalidPrioritizedItemError,
            ):
                self.logger.debug(
                    "Unable to push item %s to queue %s",
                    p_item.id,
                    self.queue.pq_id,
                    p_item_id=p_item.id,
                    queue_id=self.queue.pq_id,
                    scheduler_id=self.scheduler_id,
                )
                continue
            except Exception as exc:
                self.logger.error(
                    "Unable to push item %s to queue %s",
                    p_item.id,
                    self.queue.pq_id,
                    p_item_id=p_item.id,
                    queue_id=self.queue.pq_id,
                    scheduler_id=self.scheduler_id,
                )
                raise exc

            count += 1

    def push_item_to_queue_with_timeout(
        self,
        p_item: models.PrioritizedItem,
        max_tries: int = 5,
        timeout: int = 1,
    ) -> None:
        """Push an item to the queue, with a timeout.

        Args:
            p_item: The item to push to the queue.
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
            raise queues.errors.QueueFullError()

        self.push_item_to_queue(p_item)

    def run_in_thread(
        self,
        name: str,
        target: Callable[[], Any],
        interval: float = 0.01,
        daemon: bool = False,
        loop: bool = True,
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
            name=name,
            target=target,
            stop_event=self.stop_event_threads,
            interval=interval,
            daemon=daemon,
            loop=loop,
        )
        t.start()

        self.threads.append(t)

    def signal_handler_task(self, task: models.Task) -> None:
        """Handle a task that has been completed or failed."""
        if task.status not in [models.TaskStatus.COMPLETED, models.TaskStatus.FAILED]:
            return

        job = self.ctx.datastores.job_store.get_job_by_hash(task.p_item.hash)
        if job is None:
            return

        job.deadline_at = datetime.fromtimestamp(self.job_ranker.rank(job))
        self.ctx.datastores.job_store.update_job(job)

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
            scheduler_id=self.scheduler_id,
            status=models.TaskStatus.QUEUED,
        )
        task_ids = [task.id for task in tasks]
        self.ctx.datastores.task_store.cancel_tasks(scheduler_id=self.scheduler_id, task_ids=task_ids)

        self.logger.info("Disabled scheduler: %s", self.scheduler_id, scheduler_id=self.scheduler_id)

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

    def is_enabled(self) -> bool:
        """Check if the scheduler is enabled.

        Returns:
            True if the scheduler is enabled, False otherwise.
        """
        return self.enabled

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

    @property
    def last_activity(self) -> Optional[datetime]:
        """Get the last activity of the scheduler."""
        with self.lock:
            return self._last_activity

    @last_activity.setter
    def last_activity(self, value: datetime) -> None:
        """Set the last activity of the scheduler."""
        with self.lock:
            self._last_activity = value

    def dict(self) -> Dict[str, Any]:
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
