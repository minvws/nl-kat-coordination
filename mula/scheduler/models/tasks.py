import uuid
from datetime import datetime, timezone
from enum import Enum as _Enum
from typing import ClassVar, List, Optional

import mmh3
from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Enum, String
from sqlalchemy.sql import func

from scheduler.utils import GUID

from .base import Base
from .boefje import Boefje
from .normalizer import Normalizer
from .queue import PrioritizedItem
from .raw_data import RawData


class TaskStatus(str, _Enum):
    """Status of a task."""

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: uuid.UUID
    scheduler_id: str
    type: str
    p_item: PrioritizedItem
    status: TaskStatus

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        orm_mode = True


class TaskORM(Base):
    """A SQLAlchemy datastore model respresentation of a Task"""

    __tablename__ = "tasks"

    id = Column(GUID, primary_key=True)
    scheduler_id = Column(String)
    type = Column(String)
    p_item = Column(JSON, nullable=False)
    status = Column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDING,
    )

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


class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    type: ClassVar[str] = "normalizer"

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    normalizer: Normalizer
    raw_data: RawData

    @property
    def hash(self):
        return self.__hash__()

    def __hash__(self):
        """Make NormalizerTask hashable, so that we can de-duplicate it when
        used in the PriorityQueue. We hash the combination of the attributes
        normalizer.id since this combination is unique."""
        return mmh3.hash_bytes(
            f"{self.normalizer.id}-{self.raw_data.boefje_meta.id}-{self.raw_data.boefje_meta.organization}"
        ).hex()


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run.
    """

    type: ClassVar[str] = "boefje"

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    boefje: Boefje
    input_ooi: Optional[str]
    organization: str

    dispatches: List[Normalizer] = Field(default_factory=list)

    @property
    def hash(self):
        return self.__hash__()

    def __hash__(self) -> int:
        """Make BoefjeTask hashable, so that we can de-duplicate it when used
        in the PriorityQueue. We hash the combination of the attributes
        input_ooi and boefje.id since this combination is unique."""
        if self.input_ooi:
            return mmh3.hash_bytes(f"{self.input_ooi}-{self.boefje.id}-{self.organization}").hex()

        return mmh3.hash_bytes(f"{self.boefje.id}-{self.organization}").hex()
