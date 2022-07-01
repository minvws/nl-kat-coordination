import abc
import logging
import threading
from typing import Any, Callable, Dict, List

from scheduler import context, dispatchers, models, queues, rankers, utils
from scheduler.utils import thread


class Scheduler(abc.ABC):
    """The Scheduler class combines the priority queue, ranker and dispatcher.
    The scheduler is responsible for populating the queue, ranking, and
    dispatching tasks.

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
        dispatcher:
            A dispatchers.Dispatcher instance.
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
        dispatcher: dispatchers.Dispatcher,
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
            dispatcher:
                A dispatchers.Dispatcher instance.
            populate_queue:
                A boolean whether to populate the queue.
        """

        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.scheduler_id = scheduler_id
        self.queue: queues.PriorityQueue = queue
        self.ranker: rankers.Ranker = ranker
        self.dispatcher: dispatchers.Dispatcher = dispatcher
        self.populate_queue_enabled = populate_queue_enabled

        self.threads: Dict[str, thread.ThreadRunner] = {}
        self.stop_event: threading.Event = self.ctx.stop_event

    @abc.abstractmethod
    def populate_queue(self) -> None:
        raise NotImplementedError

    def add_p_items_to_queue(self, p_items: List[queues.PrioritizedItem]) -> None:
        """Add items to a priority queue.

        Args:
            pq: The priority queue to add items to.
            items: The items to add to the queue.
        """
        count = 0
        for p_item in p_items:
            if self.queue.full():
                self.logger.warning(
                    "Queue %s is full, not populating new tasks [queue_id=%s, qsize=%d]",
                    self.queue.pq_id,
                    self.queue.pq_id,
                    self.queue.pq.qsize(),
                )
                break

            try:
                self.queue.push(p_item)
            except queues.errors.NotAllowedError:
                self.logger.warning(
                    "Not allowed to push to queue %s [queue_id=%s, qsize=%d]",
                    self.queue.pq_id,
                    self.queue.pq_id,
                    self.queue.pq.qsize(),
                )
                continue

            count += 1

        if count > 0:
            self.logger.info(
                "Added %d items to queue: %s [queue_id=%s, count=%d]",
                count,
                self.queue.pq_id,
                self.queue.pq_id,
                count,
            )

    def _run_in_thread(
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
            self._run_in_thread(
                name="populator",
                func=self.populate_queue,
                interval=self.ctx.config.pq_populate_interval,
            )

        # Dispatcher
        if self.dispatcher is not None:
            self._run_in_thread(
                name="dispatcher",
                func=self.dispatcher.run,
                interval=self.ctx.config.dsp_interval,
            )

    def dict(self) -> Dict[str, Any]:
        return {
            "id": self.scheduler_id,
            "populate_queue_enabled": self.populate_queue_enabled,
            "priority_queue": {
                "id": self.queue.pq_id,
                "maxsize": self.queue.maxsize,
                "qsize": self.queue.pq.qsize(),
                "allow_replace": self.queue.allow_replace,
                "allow_updates": self.queue.allow_updates,
                "allow_priority_updates": self.queue.allow_priority_updates,
            },
        }
