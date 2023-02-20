import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class Boefje(BaseModel):
    """Boefje representation."""
    id: str
    version: Optional[str] = Field(default=None)


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: str
    boefje: Boefje
    input_ooi: Optional[str]
    arguments: Dict = {}
    organization: str

    started_at: Optional[datetime.datetime]
    ended_at: Optional[datetime.datetime]
