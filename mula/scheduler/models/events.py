import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import Index
from sqlalchemy.sql import func

from scheduler.utils import GUID

from .base import Base
from .raw_data import RawData


class RawDataReceivedEvent(BaseModel):
    created_at: datetime
    organization: str
    raw_data: RawData


class Event(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: uuid.UUID

    type: str

    context: str

    event: str

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    data: dict


class EventDB(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)

    task_id = Column(GUID)

    type = Column(String)

    context = Column(String)

    event = Column(String)

    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    data = Column(JSONB, nullable=False)

    __table_args__ = (
        Index(
            "ix_events_task_id",
            task_id,
        ),
    )
