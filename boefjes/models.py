from enum import Enum
from pathlib import Path
from typing import Optional, Set, List, Union

from pydantic import BaseModel, StrictBytes
from pydantic.fields import Field

BOEFJES_DIR = Path(__file__).parent


class SCAN_LEVEL(Enum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


class Boefje(BaseModel):
    id: str
    name: str
    module: Optional[str]
    description: Optional[str] = None
    consumes: Set[str]
    produces: Set[str]
    scan_level: SCAN_LEVEL = SCAN_LEVEL.L1


class Normalizer(BaseModel):
    name: str
    module: str
    consumes: Optional[List[str]] = Field(default_factory=list)
    produces: Optional[Set[str]] = Field(default_factory=set)


class RawData(BaseModel):
    data: Union[StrictBytes, str]
    mime_types: Set[str]
