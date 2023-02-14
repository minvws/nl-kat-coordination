import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Normalizer(BaseModel):
    """Normalizer representation."""

    id: Optional[str]
    name: Optional[str]
    version: Optional[str] = Field(default=None)


class NormalizerMeta(BaseModel):
    """NormalizerMeta is the response object returned by the Bytes API."""

    id: str
    normalizer: Normalizer
    raw_file_id: Optional[str]
    started_at: datetime.datetime
    ended_at: datetime.datetime
