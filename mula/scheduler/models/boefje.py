import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Boefje(BaseModel):
    """Boefje representation."""

    id: str
    version: Optional[str] = Field(default=None)
    rate_limit: Optional[str] = Field(default=None) # TODO: update when this is implemented


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: str
    boefje: Boefje
    input_ooi: Optional[str]
    arguments: Dict[str, Any] = Field(default_factory=dict)
    organization: str

    started_at: Optional[datetime.datetime]
    ended_at: Optional[datetime.datetime]
