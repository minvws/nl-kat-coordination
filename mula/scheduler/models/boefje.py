import datetime
import uuid
from typing import Any

import limits
from pydantic import BaseModel, Field, field_validator


class RateLimit(BaseModel):
    identifier: str
    interval: str

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, value: str) -> str:
        """Custom validation for the field interval."""
        try:
            limits.parse(value)
            return value
        except Exception as exc:
            raise ValueError(f"Invalid interval: {value}") from exc


class Boefje(BaseModel):
    """Boefje representation."""

    id: str
    name: str | None = None
    version: str | None = None
    rate_limit: RateLimit | None = None


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: uuid.UUID
    boefje: Boefje
    input_ooi: str | None
    arguments: dict[str, Any] = Field(default_factory=dict)
    organization: str

    started_at: datetime.datetime | None
    ended_at: datetime.datetime | None
