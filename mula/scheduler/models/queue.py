import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from scheduler.utils import GUID

from .base import Base


class PrioritizedItem(BaseModel):
    """Representation of an queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue prioritized items to a JSON
    representation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    scheduler_id: Optional[str] = None

    # A unique generated identifier for the object contained in data
    hash: Optional[str] = Field(None, max_length=32)

    priority: Optional[int]

    data: Dict

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PrioritizedItemDB(Base):
    __tablename__ = "items"

    id = Column(GUID, primary_key=True)
    scheduler_id = Column(String)
    hash = Column(String(32), index=True)
    priority = Column(Integer)
    data = Column(JSONB, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Queue(BaseModel):
    id: str
    size: int
    maxsize: int
    item_type: str
    allow_replace: bool
    allow_updates: bool
    allow_priority_updates: bool
    pq: Optional[List[PrioritizedItem]] = None
