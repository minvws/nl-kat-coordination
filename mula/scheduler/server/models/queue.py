from pydantic import BaseModel, ConfigDict

from scheduler.models import Task


class Queue(BaseModel):
    id: str
    size: int
    maxsize: int
    item_type: str
    allow_replace: bool
    allow_updates: bool
    allow_priority_updates: bool
    pq: list[Task] | None = None
