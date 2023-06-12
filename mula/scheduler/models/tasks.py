import enum
import uuid
from datetime import datetime, timezone
from typing import ClassVar, List, Optional

import mmh3
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import Index
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text

from scheduler.utils import GUID

from .base import Base
from .boefje import Boefje
from .normalizer import Normalizer
from .queue import PrioritizedItem
from .raw_data import RawData


class TaskStatus(str, enum.Enum):
    """Status of a task."""

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    id: uuid.UUID
    scheduler_id: str
    type: str
    p_item: PrioritizedItem
    status: TaskStatus

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"Task(id={self.id}, scheduler_id={self.scheduler_id}, type={self.type}, status={self.status})"

    class Config:
        orm_mode = True


class TaskORM(Base):
    """A SQLAlchemy datastore model representation of a Task"""

    __tablename__ = "tasks"

    id = Column(GUID, primary_key=True)
    scheduler_id = Column(String)
    type = Column(String)
    p_item = Column(JSONB, nullable=False)
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

    __table_args__ = (
        Index(
            "ix_p_item_hash",
            text("(p_item->>'hash')"),
            created_at.desc(),
        ),
    )


class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    type: ClassVar[str] = "normalizer"

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    normalizer: Normalizer
    raw_data: RawData

    @property
    def hash(self) -> str:
        """Make NormalizerTask hashable, so that we can de-duplicate it when
        used in the PriorityQueue. We hash the combination of the attributes
        normalizer.id since this combination is unique."""
        return mmh3.hash_bytes(
            f"{self.normalizer.id}-{self.raw_data.boefje_meta.id}-{self.raw_data.boefje_meta.organization}"
        ).hex()


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    type: ClassVar[str] = "boefje"

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    boefje: Boefje
    input_ooi: Optional[str]
    organization: str

    dispatches: List[Normalizer] = Field(default_factory=list)

    @property
    def hash(self) -> str:
        """Make BoefjeTask hashable, so that we can de-duplicate it when used
        in the PriorityQueue. We hash the combination of the attributes
        input_ooi and boefje.id since this combination is unique."""
        if self.input_ooi:
            return mmh3.hash_bytes(f"{self.input_ooi}-{self.boefje.id}-{self.organization}").hex()

        return mmh3.hash_bytes(f"{self.boefje.id}-{self.organization}").hex()
