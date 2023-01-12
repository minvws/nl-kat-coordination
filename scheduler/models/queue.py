import datetime
import uuid
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Integer, String

from scheduler.utils import GUID

from .base import Base


class PrioritizedItem(BaseModel):
    """Representation of an queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue prioritized items to a JSON
    representation.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    scheduler_id: Optional[str]

    # A unique generated identifier for the object contained in data
    hash: Optional[str]

    priority: Optional[int]

    data: Dict

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    modified_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        orm_mode = True


class PrioritizedItemORM(Base):
    """Representation of an queue.PrioritizedItem on the priority queue. Used
    for marshalling of priority queue prioritized items to a database
    representation.
    """

    __tablename__ = "items"

    id = Column(GUID, primary_key=True)
    scheduler_id = Column(String)
    hash = Column(String)

    priority = Column(Integer)
    data = Column(JSON, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
    )
    modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )


class Queue(BaseModel):
    """Representation of an queue.PriorityQueue object. Used for unmarshalling
    of priority queues to a JSON representation.
    """

    id: str
    size: int
    maxsize: int
    item_type: str
    allow_replace: bool
    allow_updates: bool
    allow_priority_updates: bool
    pq: List[PrioritizedItem]
