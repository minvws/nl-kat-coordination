import datetime
import uuid
from typing import Optional

from pydantic import BaseModel


class Normalizer(BaseModel):
    """Normalizer representation."""

    id: str
    name: Optional[str] = None
    version: Optional[str] = None


class NormalizerMeta(BaseModel):
    """NormalizerMeta is the response object returned by the Bytes API."""

    id: uuid.UUID
    normalizer: Normalizer
    raw_file_id: Optional[str]
    started_at: datetime.datetime
    ended_at: datetime.datetime
