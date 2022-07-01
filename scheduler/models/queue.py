from typing import Any, List

from pydantic import BaseModel


class QueuePrioritizedItem(BaseModel):
    """Representation of an queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue prioritized items to a JSON
    representation.
    """

    priority: int
    item: Any


class QueueEntry(BaseModel):
    """Representation of an queue.Entry on the priority queue. Used for
    for unmarshalling of priority queue entries to a JSON representation.
    """

    priority: int
    p_item: QueuePrioritizedItem
    state: str


class Queue(BaseModel):
    """Representation of an queue.PriorityQueue object. Used for unmarshalling
    of priority queues to a JSON representation.
    """

    id: str
    size: int
    maxsize: int
    allow_replace: bool
    allow_updates: bool
    allow_priority_updates: bool
    pq: List[QueueEntry]
