from __future__ import annotations

import abc
import logging
import threading
from typing import Any, Dict, List, Optional

import pydantic

from scheduler import models, repositories

from .errors import (
    InvalidPrioritizedItemError,
    NotAllowedError,
    PrioritizedItemNotFoundError,
    QueueEmptyError,
    QueueFullError,
)


class PriorityQueue(abc.ABC):
    """Base PriorityQueue class

    Attributes:
        logger:
            The logger for the class.
        pq_id:
            A string representing the identifier of the priority queue.
        maxsize:
            A integer representing the maximum size of the queue.
        item_type:
            A pydantic.BaseModel that describes the type of the items on the
            queue.
        allow_replace:
            A boolean that defines if the queue allows replacing an item. When
            set to True, it will update the item on the queue.
        allow_updates:
            A boolean that defines if the queue allows updates of items on the
            queue. When set to True, it will update the item on the queue.
        allow_priority_updates:
            A boolean that defines if the queue allows priority updates of
            items on the queue. When set to True, it will update the item on
            the queue.
        pq_store:
            A PriorityQueueStore instance that will be used to store the items
            in a persistent way.
    """

    def __init__(
        self,
        pq_id: str,
        maxsize: int,
        item_type: Any,
        pq_store: repositories.stores.PriorityQueueStorer,
        allow_replace: bool = False,
        allow_updates: bool = False,
        allow_priority_updates: bool = False,
    ):
        """Initialize the priority queue.

        Args:
            pq_id:
                The id of the queue.
            maxsize:
                The maximum size of the queue.
            item_type:
                The type of the items in the queue.
            allow_replace:
                A boolean that defines if the queue allows replacing an item.
                When set to True, it will update the item on the queue.
            allow_updates:
                A boolean that defines if the queue allows updates of items on
                the queue. When set to True, it will update the item on the
                queue.
            allow_priority_updates:
                A boolean that defines if the queue allows priority updates of
                items on the queue. When set to True, it will update the item
                on the queue.
            pq_store:
                A PriorityQueueStore instance that will be used to store the
                items in a persistent way.
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.pq_id: str = pq_id
        self.maxsize: int = maxsize
        self.item_type: Any = item_type
        self.allow_replace: bool = allow_replace
        self.allow_updates: bool = allow_updates
        self.allow_priority_updates: bool = allow_priority_updates
        self.pq_store: repositories.stores.PriorityQueueStorer = pq_store
        self.lock: threading.Lock = threading.Lock()

    def pop(self, filters: Optional[List[models.Filter]] = None) -> Optional[models.PrioritizedItem]:
        """Remove and return the highest priority item from the queue.

        Raises:
            QueueEmptyError: If the queue is empty.
        """
        with self.lock:
            if self.empty():
                raise QueueEmptyError(f"Queue {self.pq_id} is empty.")

            item = self.pq_store.pop(self.pq_id, filters)
            if item is None:
                return None

            self.remove(item)

        return item

    def push(self, p_item: models.PrioritizedItem) -> Optional[models.PrioritizedItem]:
        """Push an item onto the queue.

        Args:
            p_item: The item to be pushed onto the queue.

        Raises:
            NotAllowedError: If the item is not allowed to be pushed.

            InvalidPrioritizedItemError: If the item is not valid.

            QueueFullError: If the queue is full.

            PrioritizedItemNotFoundError: If the item is not found on the queue.
        """
        with self.lock:
            if not isinstance(p_item, models.PrioritizedItem):
                raise InvalidPrioritizedItemError("The item is not a PrioritizedItem")

            if not self._is_valid_item(p_item.data):
                raise InvalidPrioritizedItemError(f"PrioritizedItem must be of type {self.item_type}")

            if self.full():
                raise QueueFullError(f"Queue {self.pq_id} is full.")

            # We try to get the item from the queue by a specified identifier of
            # that item by the implementation of the queue. We don't do this by
            # the item itself or its hash because this might have been changed
            # and we might need to update that.
            item_on_queue = self.get_p_item_by_identifier(p_item)

            item_changed = item_on_queue and p_item.data != item_on_queue.data  # FIXM: checking json/dicts here

            priority_changed = item_on_queue and p_item.priority != item_on_queue.priority

            allowed = any(
                (
                    item_on_queue and self.allow_replace,
                    self.allow_updates and item_changed and item_on_queue,
                    self.allow_priority_updates and priority_changed and item_on_queue,
                    not item_on_queue,
                )
            )

            if not allowed:
                raise NotAllowedError(
                    f"[item_on_queue={item_on_queue}, item_changed={item_changed}, "
                    f" priority_changed={priority_changed}, "
                    f"allow_replace={self.allow_replace}, allow_updates={self.allow_updates}, "
                    f"allow_priority_updates={self.allow_priority_updates}]"
                )

            # If already on queue update the item, else create a new one
            item_db = None
            if not item_on_queue:
                identifier = self.create_hash(p_item)
                p_item.hash = identifier
                item_db = self.pq_store.push(self.pq_id, p_item)
            else:
                self.pq_store.update(self.pq_id, p_item)
                item_db = self.get_p_item_by_identifier(p_item)

            if not item_db:
                raise PrioritizedItemNotFoundError(f"Item {p_item} not found in datastore {self.pq_id}")

            return item_db

    def peek(self, index: int) -> Optional[models.PrioritizedItem]:
        """Return the item at index without removing it.

        Args:
            index: The index of the item to be returned.
        """
        return self.pq_store.peek(self.pq_id, index)

    def remove(self, p_item: models.PrioritizedItem) -> None:
        """Remove an item from the queue.

        Args:
            p_item: The item to be removed from the queue.
        """
        self.pq_store.remove(self.pq_id, str(p_item.id))

    def clear(self) -> None:
        """Clear the queue."""
        self.pq_store.clear(self.pq_id)

    def empty(self) -> bool:
        """Return True if the queue is empty, False otherwise."""
        return self.pq_store.empty(self.pq_id)

    def qsize(self) -> int:
        """Return the size of the queue."""
        return self.pq_store.qsize(self.pq_id)

    def full(self) -> bool:
        """Return True if the queue is full, False otherwise."""
        current_size = self.qsize()
        if self.maxsize is None or self.maxsize == 0:
            return False

        return current_size >= self.maxsize

    def is_item_on_queue(self, p_item: models.PrioritizedItem) -> bool:
        """Check if an item is on the queue.

        Args:
            p_item: The item to be checked.

        Returns:
            True if the item is on the queue, False otherwise.
        """
        identifier = self.create_hash(p_item)
        item = self.pq_store.get_item_by_hash(self.pq_id, identifier)
        if item is None:
            return False

        return True

    def is_item_on_queue_by_hash(self, item_hash: str) -> bool:
        """Check if an item is on the queue by its hash.

        Args:
            item_hash: The hash of the item to be checked.

        Returns:
            True if the item is on the queue, False otherwise.
        """
        item = self.pq_store.get_item_by_hash(self.pq_id, item_hash)
        return item is not None

    def get_p_item_by_identifier(self, p_item: models.PrioritizedItem) -> Optional[models.PrioritizedItem]:
        """Get an item from the queue by its identifier.

        Args:
            p_item: The item to be checked.

        Returns:
            The item if found, None otherwise.
        """
        identifier = self.create_hash(p_item)
        item = self.pq_store.get_item_by_hash(self.pq_id, identifier)
        return item

    def _is_valid_item(self, item: Any) -> bool:
        """Validate the item to be pushed into the queue.

        Args:
            item: The item to be validated.

        Returns:
            A boolean, True if the item is valid, False otherwise.
        """
        try:
            self.item_type.parse_obj(item)
        except pydantic.ValidationError:
            return False

        return True

    def dict(self, include_pq: bool = True) -> Dict[str, Any]:
        """Return a dictionary representation of the queue."""
        response = {
            "id": self.pq_id,
            "size": self.qsize(),
            "maxsize": self.maxsize,
            "item_type": self.item_type.__name__,
            "allow_replace": self.allow_replace,
            "allow_updates": self.allow_updates,
            "allow_priority_updates": self.allow_priority_updates,
        }

        if include_pq:
            response["pq"] = self.pq_store.get_items_by_scheduler_id(self.pq_id)

        return response

    @abc.abstractmethod
    def create_hash(self, p_item: models.PrioritizedItem) -> str:
        """Create a hash for the item.

        Abstract method to be implemented by the concrete implementation of
        the queue. It needs to create a unique identifier for the item on
        the queue.

        Args:
            p_item: The item to be hashed.

        Returns:
            A string representing the hash of the item.
        """
        raise NotImplementedError
