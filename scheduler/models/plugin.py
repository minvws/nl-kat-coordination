import datetime
from typing import List, Optional, Union

from pydantic import BaseModel


class Plugin(BaseModel):
    id: str
    name: Optional[str]
    version: Optional[str]
    authors: Optional[List[str]]
    created: Optional[datetime.datetime]
    description: Optional[str]
    environment_keys: Optional[List[str]]
    related: Optional[List[str]]
    type: str
    scan_level: Optional[int]
    consumes: Union[str, List[str]]
    options: Optional[List[str]]
    produces: List[str]
    enabled: bool
