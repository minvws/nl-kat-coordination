from datetime import datetime, timezone

from pydantic import BaseModel, Field

from bytes.models import RawDataMeta


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(BaseModel):
    event_id: str

    created_at: datetime = Field(default_factory=utc_now)  # Needs to be a callable, hence the wrapping
    organization: str


class RawFileReceived(Event):
    event_id: str = "raw_file_received"

    raw_data: RawDataMeta
