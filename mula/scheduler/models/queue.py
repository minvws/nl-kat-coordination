import enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from scheduler.utils import GUID

from .base import Base
from .task import Task, TaskStatus

# Make PrioritizedItemStatus an enum of TaskStatus
PrioritizedItemStatus = enum.Enum("PrioritizedItemStatus", TaskStatus.__members__)


class PrioritizedItem(Task):
    pass


class Queue(BaseModel):
    id: str
    size: int
    maxsize: int
    item_type: str
    allow_replace: bool
    allow_updates: bool
    allow_priority_updates: bool
    pq: list[PrioritizedItem] | None = None
