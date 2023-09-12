import datetime
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Boefje(BaseModel):
    """Boefje representation."""

    id: str
    name: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: uuid.UUID
    boefje: Boefje
    input_ooi: Optional[str]
    arguments: Dict[str, Any] = Field(default_factory=dict)
    organization: str

    started_at: Optional[datetime.datetime]
    ended_at: Optional[datetime.datetime]
