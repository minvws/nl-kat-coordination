import datetime
import uuid

from pydantic import BaseModel, Field


class Normalizer(BaseModel):
    """Normalizer representation."""

    id: str
    name: str | None = Field(default=None)
    version: str | None = Field(default=None)


class NormalizerMeta(BaseModel):
    """NormalizerMeta is the response object returned by the Bytes API."""

    id: uuid.UUID
    normalizer: Normalizer
    raw_file_id: str | None
    started_at: datetime.datetime
    ended_at: datetime.datetime
