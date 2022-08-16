import datetime
import uuid
from enum import Enum as _Enum
from typing import List, Optional

import mmh3
from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Enum, String

from scheduler.utils import GUID

from .base import Base
from .boefje import Boefje, BoefjeMeta
from .normalizer import Normalizer
from .queue import QueuePrioritizedItem


class TaskStatus(_Enum):
    """Status of a task."""

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: uuid.UUID
    hash: str
    scheduler_id: str
    task: QueuePrioritizedItem  # FIXME: p_item?
    status: TaskStatus
    created_at: datetime.datetime
    modified_at: datetime.datetime

    class Config:
        orm_mode = True


class TaskORM(Base):
    """A SQLAlchemy datastore model respresentation of a Task"""

    __tablename__ = "tasks"

    id = Column(GUID, primary_key=True)
    hash = Column(String)
    scheduler_id = Column(String)
    task = Column(JSON, nullable=False)
    status = Column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDING,
    )
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


class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    id: Optional[str]
    normalizer: Normalizer
    boefje_meta: BoefjeMeta

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = uuid.uuid4().hex

    @property
    def hash(self):
        return self.__hash__()

    def __hash__(self):
        """Make NormalizerTask hashable, so that we can de-duplicate it when
        used in the PriorityQueue. We hash the combination of the attributes
        normalizer.id since this combination is unique."""
        return mmh3.hash_bytes(f"{self.normalizer.id}-{self.boefje_meta.id}").hex()


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    id: Optional[str]
    boefje: Boefje
    input_ooi: str
    organization: str

    dispatches: List[Normalizer] = Field(default_factory=list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = uuid.uuid4().hex

    @property
    def hash(self):
        return self.__hash__()

    def __hash__(self) -> int:
        """Make BoefjeTask hashable, so that we can de-duplicate it when used
        in the PriorityQueue. We hash the combination of the attributes
        input_ooi and boefje.id since this combination is unique."""
        return mmh3.hash_bytes(f"{self.input_ooi}-{self.boefje.id}-{self.organization}").hex()
