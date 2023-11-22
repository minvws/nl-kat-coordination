import enum
import uuid
from datetime import datetime, timezone
from typing import ClassVar, List, Optional

import mmh3
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DDL, Column, DateTime, Enum, String, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
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

    _event_store = None

    @classmethod
    def set_event_store(cls, event_store):
        cls._event_store = event_store

    @hybrid_property
    def duration(self) -> float:
        if self._event_store is None:
            raise ValueError("EventStore instance is not set. Use TaskDB.set_event_store to set it.")

        return self._event_store.get_task_duration(self.id)

    @hybrid_property
    def queued(self) -> float:
        if self._event_store is None:
            raise ValueError("EventStore instance is not set. Use TaskDB.set_event_store to set it.")

        return self._event_store.get_task_queued(self.id)

    @hybrid_property
    def runtime(self) -> float:
        if self._event_store is None:
            raise ValueError("EventStore instance is not set. Use TaskDB.set_event_store to set it.")

        return self._event_store.get_task_runtime(self.id)

    @hybrid_property
    def cpu(self) -> float:
        if self._event_store is None:
            raise ValueError("EventStore instance is not set. Use TaskDB.set_event_store to set it.")

        return self._event_store.get_task_cpu(self.id)

    @hybrid_property
    def memory(self) -> float:
        if self._event_store is None:
            raise ValueError("EventStore instance is not set. Use TaskDB.set_event_store to set it.")

        return self._event_store.get_task_memory(self.id)

    @hybrid_property
    def disk(self) -> float:
        if self._event_store is None:
            raise ValueError("EventStore instance is not set. Use TaskDB.set_event_store to set it.")

        return self._event_store.get_task_disk(self.id)

    @hybrid_property
    def network(self) -> float:
        if self._event_store is None:
            raise ValueError("EventStore instance is not set. Use TaskDB.set_event_store to set it.")

        return self._event_store.get_task_network(self.id)


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    scheduler_id: str

    type: str

    p_item: PrioritizedItem

    status: TaskStatus

    duration: Optional[float] = Field(None, alias="duration", readonly=True)

    queued: Optional[float] = Field(None, alieas="queued", readonly=True)

    runtime: Optional[float] = Field(None, alias="runtime", readonly=True)

    cpu: Optional[float] = Field(None, alias="cpu", readonly=True)

    memory: Optional[float] = Field(None, alias="memory", readonly=True)

    disk: Optional[float] = Field(None, alias="disk", readonly=True)

    network: Optional[float] = Field(None, alias="network", readonly=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"Task(id={self.id}, scheduler_id={self.scheduler_id}, type={self.type}, status={self.status})"

    def model_dump_db(self):
        return self.model_dump(exclude={"duration", "queued", "runtime", "cpu", "memory", "disk", "network"})


class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    type: ClassVar[str] = "normalizer"

    id: uuid.UUID = Field(default_factory=lambda: uuid.uuid4())
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

    id: uuid.UUID = Field(default_factory=lambda: uuid.uuid4())
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


func_record_event = DDL("""
    CREATE OR REPLACE FUNCTION record_event()
        RETURNS TRIGGER AS
    $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            INSERT INTO events (task_id, type, context, event, data)
            VALUES (NEW.id, 'events.db', 'task', 'insert', row_to_json(NEW));
        ELSIF TG_OP = 'UPDATE' THEN
            INSERT INTO events (task_id, type, context, event, data)
            VALUES (NEW.id, 'events.db', 'task', 'update', row_to_json(NEW));
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
""")

trigger_tasks_insert_update = DDL("""
    CREATE TRIGGER tasks_insert_update_trigger
    AFTER INSERT OR UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION record_event();
""")

event.listen(TaskDB.__table__, "after_create", func_record_event.execute_if(dialect="postgresql"))
event.listen(TaskDB.__table__, "after_create", trigger_tasks_insert_update.execute_if(dialect="postgresql"))
