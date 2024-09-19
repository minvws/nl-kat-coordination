import datetime
import uuid
from typing import Any

from pydantic import BaseModel, Field


class Boefje(BaseModel):
    """Boefje representation."""

    id: str
    name: str | None = Field(default=None)
    version: str | None = Field(default=None)


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: uuid.UUID
    boefje: Boefje
    input_ooi: str | None
    arguments: dict[str, Any] = Field(default_factory=dict)
    organization: str

    started_at: datetime.datetime | None
    ended_at: datetime.datetime | None
