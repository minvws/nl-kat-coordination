from datetime import datetime

from pydantic import BaseModel
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


class EventDB(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)

    task_id = Column(GUID)

    type = Column(String)

    context = Column(String)

    event = Column(String)

    datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    data = Column(JSONB, nullable=False)

    __table_args__ = (
        Index(
            "ix_events_task_id",
            task_id,
        ),
    )
