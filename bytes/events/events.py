from datetime import datetime, timezone

from pydantic import BaseModel, Field

from bytes.models import RawDataMeta, NormalizerMeta


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(BaseModel):
    created_at: datetime = Field(default_factory=utc_now)  # Needs to be a callable, hence the wrapping
    organization: str

    # Starting with underscore means it is ignored by pydantic
    _event_id: str


class RawFileReceived(Event):
    _event_id: str = "raw_file_received"

    raw_data: RawDataMeta


class NormalizerMetaReceived(Event):
    _event_id: str = "normalizer_meta_received"

    normalizer_meta: NormalizerMeta
