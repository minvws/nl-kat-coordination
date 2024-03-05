import enum
import uuid
from datetime import datetime, timezone
from typing import ClassVar

import mmh3
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Enum, Interval, String
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
    # Task has been created but not yet queued
    PENDING = "pending"

    # Task has been pushed onto queue and is ready to be picked up
    QUEUED = "queued"

    # Task has been picked up by a worker
    DISPATCHED = "dispatched"

    # Task has been picked up by a worker, and the worker indicates that it is
    # running.
    RUNNING = "running"

    # Task has been completed
    COMPLETED = "completed"

    # Task has failed
    FAILED = "failed"

    # Task has been cancelled
    CANCELLED = "cancelled"


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    scheduler_id: str

    type: str

    p_item: PrioritizedItem

    status: TaskStatus

    meta: Optional[dict] = None

    # Status transition timestamps
    pending_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    queued_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    running_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def update_status(self, status: TaskStatus) -> None:
        """Update and log the status transition."""
        from_status = self.status
        to_status = status
        now_utc = datetime.now(timezone.utc)

        if from_status == TaskStatus.PENDING and to_status in (TaskStatus.QUEUED,):
            self.queued_at = now_utc
        elif from_status == TaskStatus.QUEUED and to_status in (TaskStatus.DISPATCHED,):
            self.dispatched_at = now_utc
        elif from_status == TaskStatus.DISPATCHED and to_status in (TaskStatus.RUNNING,):
            self.running_at = now_utc
        elif from_status == TaskStatus.RUNNING and to_status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            self.completed_at = now_utc

        self.status = to_status

    def __repr__(self):
        return f"Task(id={self.id}, scheduler_id={self.scheduler_id}, type={self.type}, status={self.status})"


class TaskDB(Base):
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

    meta = Column(JSONB)

    pending_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    queued_at = Column(DateTime(timezone=True), nullable=True)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    running_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

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

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4)
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

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4)
    boefje: Boefje
    input_ooi: str | None
    organization: str

    dispatches: list[Normalizer] = Field(default_factory=list)

    @property
    def hash(self) -> str:
        """Make BoefjeTask hashable, so that we can de-duplicate it when used
        in the PriorityQueue. We hash the combination of the attributes
        input_ooi and boefje.id since this combination is unique."""
        if self.input_ooi:
            return mmh3.hash_bytes(f"{self.input_ooi}-{self.boefje.id}-{self.organization}").hex()

        return mmh3.hash_bytes(f"{self.boefje.id}-{self.organization}").hex()
