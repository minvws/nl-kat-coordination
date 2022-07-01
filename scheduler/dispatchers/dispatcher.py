import logging
from typing import Any, Type

import celery
import pydantic
import scheduler
from scheduler import context, queues


class Dispatcher:
    """Dispatcher allows to continuously pop items off a priority queue and
    dispatches items to be handled. By what, and who, this is being handled is
    done by a sub-classing and extending the dispatcher and implementing the
    `dispatch()` method.

    Attributes:
        logger:
            The logger for the class.
        pq:
            A queue.PriorityQueue instance.
        threshold:
            A float describing the threshold that needs to be adhered too
            for dispatching tasks from the priority queue. By default this is
            set to `float("inf")` meaning all the items on the queue are
            allowed to be dispatched. Set this threshold by implementing
            the `get_threshold` method.
        item_type:
            A pydantic.BaseModel object that specifies the type of item that
            should be dispatched, this helps with validation.
    """

    def __init__(self, pq: queues.PriorityQueue, item_type: Type[pydantic.BaseModel]):
        """Initialize the Dispatcher class

        Args:
            pq:
                A queue.PriorityQueue instance.
            item_type:
                A pydantic.BaseModel object that specifies the type of item
                that should be dispatched, this helps with validation.
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.pq: queues.PriorityQueue = pq
        self.threshold: float = float("inf")
        self.item_type: Type[pydantic.BaseModel] = item_type

    def _can_dispatch(self) -> bool:
        """Checks the first item of the priority queue, whether or not items
        priority higher in priority and thus lower or equal to the defined
        threshold should be dispatched.

        Returns:
            A boolean representing whether the item with the highest priority
            on the queue, should be dispatched.
        """
        p_item = self.pq.peek(0).p_item
        if float(p_item.priority) <= self.get_threshold():
            return True

        return False

    def _is_valid_item(self, item: Any) -> bool:
        """Check if an item is of the same type as the defined item_type

        Args:
            item: typing.Any

        Returns:
            A boolean
        """
        try:
            self.item_type.parse_obj(item)
            return True
        except pydantic.ValidationError:
            return False

    def get_threshold(self) -> float:
        """Return the threshold of that needs to be adhered to.

        Returns:
            A float returning the threshold attribute.
        """
        return self.threshold

    def dispatch(self, p_item: queues.PrioritizedItem) -> None:
        """Pop and dispatch a task item from a priority queue entry. This
        method should be extended by subclasses to implement its specific
        dispatching strategy.

        Arguments:
            p_item:
                A queues.PrioritizedItem instance.

        Returns:
            None
        """
        task_id = self.pq.get_item_identifier(p_item.item)
        self.logger.info(
            "Dispatching task %s [task_id=%s, pq_id=%s]",
            task_id,
            task_id,
            self.pq.pq_id,
        )

    def run(self) -> None:
        """Continuously dispatch items from the priority queue."""
        if self.pq.empty():
            self.logger.debug("Queue is empty, sleeping ... [pq_id=%s]", self.pq.pq_id)
            return

        if not self._can_dispatch():
            # self.logger.debug("Can't yet dispatch, threshold not reached")
            return

        p_item = self.pq.pop()

        if not self._is_valid_item(p_item.item):
            raise ValueError(f"Item must be of type {self.item_type}")

        self.dispatch(p_item=p_item)


class CeleryDispatcher(Dispatcher):
    """A Celery implementation of a Dispatcher.

    Attributes:
        ctx:
            A context.AppContext instance.
        celery_queue:
            A string descibing the Celery queue to which the tasks need to
            be dispatched.
        task_name:
            A string describing the name of the Celery task
    """

    def __init__(
        self,
        ctx: context.AppContext,
        pq: queues.PriorityQueue,
        item_type: Type[pydantic.BaseModel],
        celery_queue: str,
        task_name: str,
    ):
        """Initialize the CeleryDispatcher class.

        Args:
            ctx:
                A contex.AppContext instance.
            pq:
                A queue.PriorityQueue instance.
            item_type:
                A pydantic.BaseModel object that specifies the type of item
                that should be dispatched, this helps with validation.
            celery_queue:
                A string descibing the Celery queue to which the tasks need to
                be dispatched.
            task_name:
                A string describing the name of the Celery task
        """
        super().__init__(pq=pq, item_type=item_type)

        self.ctx = ctx
        self.celery_queue = celery_queue
        self.task_name = task_name

        self.app = celery.Celery(
            name=f"scheduler-{scheduler.__version__}",
            broker=self.ctx.config.dsp_broker_url,
        )

        self.app.conf.update(
            task_serializer="json",
            result_serializer="json",
            event_serializer="json",
            accept_content=["application/json", "application/x-python-serialize"],
            result_accept_content=["application/json", "application/x-python-serialize"],
        )

    def dispatch(self, p_item: queues.PrioritizedItem) -> None:
        super().dispatch(p_item=p_item)

        item_dict = p_item.item.dict()

        self.app.send_task(
            name=self.task_name,
            args=(item_dict,),
            queue=self.celery_queue,
            task_id=item_dict.get("id"),
        )
