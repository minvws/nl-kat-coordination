import datetime
from enum import Enum
from typing import List, Literal, NewType, Optional, Set, Union

from pydantic import AnyHttpUrl, BaseModel, Field

RESERVED_LOCAL_ID = "LOCAL"


class Repository(BaseModel):
    id: str
    name: str
    base_url: AnyHttpUrl


class Organisation(BaseModel):
    id: str
    name: str


class Plugin(BaseModel):
    id: str
    repository_id: str = RESERVED_LOCAL_ID
    name: Optional[str] = None
    version: Optional[str] = None
    authors: Optional[List[str]] = None
    created: Optional[datetime.datetime] = None
    description: Optional[str] = None
    environment_keys: List[str] = Field(default_factory=list)
    related: Optional[List[str]] = None
    enabled: bool = False

    def __str__(self):
        return f"{self.id}:{self.version}"


class Boefje(Plugin):
    type: Literal["boefje"] = "boefje"
    scan_level: int = 1
    consumes: Set[str] = Field(default_factory=set)
    produces: List[str] = Field(default_factory=list)
    options: Optional[List[str]] = None
    runnable_hash: Optional[str] = None
    oci_image: Optional[str] = None


class Normalizer(Plugin):
    type: Literal["normalizer"] = "normalizer"
    consumes: List[str] = Field(default_factory=list)  # mime types (and/ or boefjes)
    produces: List[str] = Field(default_factory=list)  # oois
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
