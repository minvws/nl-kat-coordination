import abc
import logging
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from scheduler import connectors, context, models, queues, utils
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

        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.enabled: bool = True
        self.scheduler_id: str = scheduler_id
        self.queue: queues.PriorityQueue = queue

        self.max_tries: int = max_tries

        self.callback: Optional[Callable[[], Any]] = callback

        # Listeners
        self.listeners: Dict[str, connectors.listeners.Listener] = {}

        # Threads
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
        # NOTE: we set the id of the task the same as the p_item, for easier
        # lookup.
        task = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler_id,
            type=self.queue.item_type.type,
            p_item=p_item,
            status=models.TaskStatus.QUEUED,
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
        # NOTE: we set the id of the task the same as the p_item, for easier
        # lookup.
        task = self.ctx.datastores.task_store.get_task_by_id(str(p_item.id))
        if task is None:
            self.logger.warning(
                "Task %s not found in datastore, not updating status [task_id=%s, queue_id=%s]",
                p_item.data.get("id"),
                p_item.data.get("id"),
                self.queue.pq_id,
            )
            return None

        task.status = models.TaskStatus.DISPATCHED
        self.ctx.datastores.task_store.update_task(task)

        return None

    def pop_item_from_queue(self, filters: Optional[List[models.Filter]] = None) -> Optional[models.PrioritizedItem]:
        """Pop an item from the queue.

        Args:
            filters: A list of filters to apply to get a filtered set of
            prioritized items from the queue.

        Returns:
            A PrioritizedItem instance.
        """
        if not self.is_enabled():
            self.logger.warning(
                "Scheduler is disabled, not popping item from queue [queue_id=%s, qsize=%d]",
                self.queue.pq_id,
                self.queue.qsize(),
            )
            raise queues.errors.NotAllowedError("Scheduler is disabled")

        try:
            p_item = self.queue.pop(filters)
        except queues.QueueEmptyError as exc:
            raise exc

        if p_item is not None:
            self.post_pop(p_item)

        return p_item

    def push_item_to_queue(self, p_item: models.PrioritizedItem) -> None:
        """Push a PrioritizedItem to the queue.

        Args:
            p_item: The PrioritizedItem to push to the queue.
        """
        if not self.is_enabled():
            self.logger.warning(
                "Scheduler is disabled, not pushing item to queue [queue_id=%s, qsize=%d]",
                self.queue.pq_id,
                self.queue.qsize(),
            )
            raise queues.errors.NotAllowedError("Scheduler is disabled")

        try:
            self.queue.push(p_item)
        except queues.errors.NotAllowedError as exc:
            self.logger.warning(
                "Not allowed to push to queue %s [queue_id=%s, qsize=%d]",
                self.queue.pq_id,
                self.queue.pq_id,
                self.queue.qsize(),
            )
            raise exc
        except queues.errors.QueueFullError as exc:
            self.logger.warning(
                "Queue %s is full, not populating new tasks [queue_id=%s, qsize=%d]",
                self.queue.pq_id,
                self.queue.pq_id,
                self.queue.qsize(),
            )
            raise exc
        except queues.errors.InvalidPrioritizedItemError as exc:
            self.logger.warning(
                "Invalid prioritized item %s [queue_id=%s, qsize=%d]",
                p_item,
                self.queue.pq_id,
                self.queue.qsize(),
            )
            raise exc

        self.logger.debug(
            "Pushed item (%s) to queue %s with priority %s "
            "[p_item_id=%s, p_item_hash=%s, queue_pq_id=%s, queue_qsize=%d]",
            p_item.id,
            self.queue.pq_id,
            p_item.priority,
            p_item.id,
            p_item.hash,
            self.queue.pq_id,
            self.queue.qsize(),
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
                    "Unable to push item to queue %s [queue_id=%s, qsize=%d, item=%s, exc=%s]",
                    self.queue.pq_id,
                    self.queue.pq_id,
                    self.queue.qsize(),
                    p_item,
                    traceback.format_exc(),
                )
                continue
            except Exception as exc:
                self.logger.error(
                    "Unable to push item to queue %s [queue_id=%s, qsize=%d, item=%s]",
                    self.queue.pq_id,
                    self.queue.pq_id,
                    self.queue.qsize(),
                    p_item,
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
                "Queue %s is full, waiting for space [queue_id=%s, qsize=%d]",
                self.queue.pq_id,
                self.queue.pq_id,
                self.queue.qsize(),
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
            self.logger.debug("Scheduler is already disabled")
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

        self.logger.info("Disabled scheduler: %s", self.scheduler_id)

    def enable(self) -> None:
        """Enable the scheduler.

        This will start the scheduler, and start all listeners and threads.
        """
        if self.is_enabled():
            self.logger.debug("Scheduler is already enabled")
            return

        self.logger.info("Enabling scheduler: %s", self.scheduler_id)
        self.enabled = True

        self.stop_event_threads.clear()

        self.run()

        self.logger.info("Enabled scheduler: %s", self.scheduler_id)

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
        self.logger.info("Stopping scheduler: %s", self.scheduler_id)

        # First, stop the listeners, when those are running in a thread and
        # they're using rabbitmq, they will block. Setting the stop event
        # will not stop the thread. We need to explicitly stop the listener.
        self.stop_listeners()
        self.stop_threads()

        if self.callback and callback:
            self.callback(self.scheduler_id)  # type: ignore [call-arg]

        self.logger.info("Stopped scheduler: %s", self.scheduler_id)

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
        }
