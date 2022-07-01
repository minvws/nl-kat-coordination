import datetime
from enum import Enum
from typing import Union, NewType, Optional, List, Literal, Set

from pydantic import BaseModel, AnyHttpUrl


class Repository(BaseModel):
    id: str
    name: str
    base_url: AnyHttpUrl


class Organisation(BaseModel):
    id: str
    name: str


class Plugin(BaseModel):
    id: str
    repository_id: str
    name: Optional[str]
    version: Optional[str]
    authors: Optional[List[str]]
    created: Optional[datetime.datetime]
    description: Optional[str]
    environment_keys: Optional[List[str]]
    related: Optional[List[str]]
    enabled: bool = False

    def __str__(self):
        return f"{self.id}:{self.version}"


class Boefje(Plugin):
    type: Literal["boefje"] = "boefje"
    scan_level: int = 1
    consumes: Set[str]
    options: Optional[List[str]]
    produces: List[str]  # mime types


class Normalizer(Plugin):
    type: Literal["normalizer"] = "normalizer"
    consumes: List[str]  # mime types (and/ or boefjes)
    produces: List[str]  # oois
    enabled: bool = True


class Bit(Plugin):
    type: Literal["bit"] = "bit"
    consumes: str
    produces: List[str]
    parameters: List[str]  # ooi.relation-name
    enabled: bool = True


PluginType = Union[Boefje, Normalizer, Bit]
Base64Str = NewType("Base64Str", str)


class EncryptionMiddleware(Enum):
    IDENTITY = "IDENTITY"
    NACL_SEALBOX = "NACL_SEALBOX"
