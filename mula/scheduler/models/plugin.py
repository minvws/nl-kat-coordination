import datetime
from typing import List, Optional, Union

from pydantic import BaseModel


class Plugin(BaseModel):
    id: str
    type: str
    enabled: bool
    name: Optional[str] = None
    version: Optional[str] = None
    authors: Optional[List[str]] = None
    created: Optional[datetime.datetime] = None
    description: Optional[str] = None
    environment_keys: Optional[List[str]] = None
    related: Optional[List[str]] = None
    scan_level: Optional[int] = None
    consumes: Union[str, List[str]]
    options: Optional[List[str]] = None
    produces: List[str]
