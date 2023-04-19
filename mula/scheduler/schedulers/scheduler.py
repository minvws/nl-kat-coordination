import abc
import logging
import threading
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from scheduler import context, models, queues, rankers, utils
from scheduler.utils import thread


class Scheduler(abc.ABC):
    """The Scheduler class combines the priority queue, and ranker.
    The scheduler is responsible for populating the queue, and ranking tasks.

    An implementation of the Scheduler will likely implement the
    `populate_queue` method, with the strategy for populating the queue. By
    extending this you can create your own rules of what items should be
    ranked and put onto the priority queue.

    Attributes:
        logger:
            The logger for the class
        ctx:
            Application context of shared data (e.g. configuration, external
            services connections).
        scheduler_id:
            The id of the scheduler.
        queue:
            A queues.PriorityQueue instance
        ranker:
            A rankers.Ranker instance.
        populate_queue_enabled:
            A boolean whether to populate the queue.
        threads:
            A dict of ThreadRunner instances, used for runner processes
            concurrently.
        stop_event: A threading.Event object used for communicating a stop
            event across threads.
    """

    organisation: models.Organisation

    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        queue: queues.PriorityQueue,
        ranker: rankers.Ranker,
        populate_queue_enabled: bool = True,
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
            populate_queue:
                A boolean whether to populate the queue.
        """

        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.scheduler_id = scheduler_id
        self.queue: queues.PriorityQueue = queue
        self.ranker: rankers.Ranker = ranker
        self.populate_queue_enabled = populate_queue_enabled

        self.threads: Dict[str, thread.ThreadRunner] = {}
        self.stop_event: threading.Event = self.ctx.stop_event

    @abc.abstractmethod
    def populate_queue(self) -> None:
        raise NotImplementedError

    def post_push(self, p_item: models.PrioritizedItem) -> None:
        """When a boefje task is being added to the queue. We
        persist a task to the datastore with the status QUEUED

        Args:
            p_item: The prioritized item to post-add to queue.
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

        task_db = self.ctx.task_store.get_task_by_id(str(p_item.id))
        if task_db is not None:
            self.ctx.task_store.update_task(task)
            return

        self.ctx.task_store.create_task(task)

    def post_pop(self, p_item: models.PrioritizedItem) -> None:
        """When a boefje task is being removed from the queue. We
        persist a task to the datastore with the status RUNNING

        Args:
            p_item: The prioritized item to post-pop from queue.
        """
        # NOTE: we set the id of the task the same as the p_item, for easier
        # lookup.
        task = self.ctx.task_store.get_task_by_id(str(p_item.id))
        if task is None:
            self.logger.warning(
                "Task %s not found in datastore, not updating status [task_id=%s, queue_id=%s]",
                p_item.data.get("id"),
                p_item.data.get("id"),
                self.queue.pq_id,
            )
            return None

        task.status = models.TaskStatus.DISPATCHED
        self.ctx.task_store.update_task(task)

        return None

    def pop_item_from_queue(self, filters: Optional[List[models.Filter]] = None) -> Optional[models.PrioritizedItem]:
        """Pop an item from the queue.

        Returns:
            A PrioritizedItem instance.
        """
        try:
            p_item = self.queue.pop(filters)
        except queues.QueueEmptyError as exc:
            raise exc

        if p_item is not None:
            self.post_pop(p_item)

        return p_item

    def push_item_to_queue(self, p_item: models.PrioritizedItem) -> None:
        """Push an item to the queue.

        Args:
            item: The item to push to the queue.
        """
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
            "[p_item.id=%s, p_item.hash=%s, queue.pq_id=%s, queue.qsize=%d]",
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
        """Add items to a priority queue.

        Args:
            pq: The priority queue to add items to.
            items: The items to add to the queue.
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

    def run_in_thread(
        self,
        name: str,
        func: Callable[[], Any],
        interval: float = 0.01,
        daemon: bool = False,
    ) -> None:
        """Make a function run in a thread, and add it to the dict of threads.

        Args:
            name: The name of the thread.
            func: The function to run in the thread.
            interval: The interval to run the function.
            daemon: Whether the thread should be a daemon.
        """
        self.threads[name] = utils.ThreadRunner(
            target=func,
            stop_event=self.stop_event,
            interval=interval,
            daemon=daemon,
        )
        self.threads[name].start()

    def stop(self) -> None:
        """Stop the scheduler."""
        for t in self.threads.values():
            t.join(5)

        self.logger.info("Stopped scheduler: %s", self.scheduler_id)

    def run(self) -> None:
        # Populator
        if self.populate_queue_enabled:
            self.run_in_thread(
                name="populator",
                func=self.populate_queue,
                interval=self.ctx.config.pq_populate_interval,
            )

    def dict(self) -> Dict[str, Any]:
        return {
            "id": self.scheduler_id,
            "populate_queue_enabled": self.populate_queue_enabled,
            "priority_queue": {
                "id": self.queue.pq_id,
                "maxsize": self.queue.maxsize,
                "qsize": self.queue.qsize(),
                "allow_replace": self.queue.allow_replace,
                "allow_updates": self.queue.allow_updates,
                "allow_priority_updates": self.queue.allow_priority_updates,
            },
        }
