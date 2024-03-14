import uuid
from datetime import datetime, timezone
from typing import ClassVar

import mmh3
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text

from scheduler.utils import GUID, cron

from .base import Base
from .boefje import Boefje
from .errors import ValidationError
from .normalizer import Normalizer
from .raw_data import RawData
from .task_run import TaskRun


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    hash: str | None = Field(None, max_length=32)
    data: dict = Field(default_factory=dict)

    schedule: str | None = None

    task_runs: list[TaskRun] = []

    deadline_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # TODO: pydantic validator?
    def validate_schedule(self):
        """Validate the schedule cron expression."""
        if self.cron_expression is not None:
            try:
                cron.next_run(self.cron_expression)
            except Exception as exc:
                raise ValidationError(f"Invalid cron expression: {self.cron_expression}") from exc


class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(GUID, primary_key=True)
    hash = Column(String(32), nullable=True)  # TODO: unique=True
    data = Column(JSONB, nullable=False)

    # TODO: cascade
    task_runs = relationship("TaskRunDB", back_populates="task")
    p_item = relationship("PrioritizedItemDB", uselist=False, back_populates="task")

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
    input_ooi: str | None = None
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
