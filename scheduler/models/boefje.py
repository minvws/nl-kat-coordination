import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class Boefje(BaseModel):
    """Boefje representation."""

    id: str
    name: Optional[str]
    description: Optional[str]
    version: Optional[str] = Field(default=None)
    scan_level: Optional[int] = Field(default=None)
    consumes: Optional[Union[str, List[str]]]
    produces: Optional[List[str]]
    dispatches: Optional[Dict[str, List[str]]] = Field(default=None)


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: str
    boefje: Boefje
    input_ooi: str
    arguments: Dict[str, Any]
    organization: str
    started_at: Optional[datetime.datetime]
    ended_at: Optional[datetime.datetime]
