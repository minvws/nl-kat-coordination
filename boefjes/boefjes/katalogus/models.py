import datetime
from enum import Enum
from typing import Literal, NewType

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
    name: str | None = None
    version: str | None = None
    authors: list[str] | None = None
    created: datetime.datetime | None = None
    description: str | None = None
    environment_keys: list[str] = Field(default_factory=list)
    related: list[str] | None = None
    enabled: bool = False

    def __str__(self):
        return f"{self.id}:{self.version}"


class Boefje(Plugin):
    type: Literal["boefje"] = "boefje"
    scan_level: int = 1
    consumes: set[str] = Field(default_factory=set)
    produces: set[str] = Field(default_factory=set)
    options: list[str] | None = None
    runnable_hash: str | None = None
    oci_image: str | None = None


class Normalizer(Plugin):
    type: Literal["normalizer"] = "normalizer"
    consumes: list[str] = Field(default_factory=list)  # mime types (and/ or boefjes)
    produces: list[str] = Field(default_factory=list)  # oois
    enabled: bool = True


class Bit(Plugin):
    type: Literal["bit"] = "bit"
    consumes: str
    produces: list[str]
    parameters: list[str]  # ooi.relation-name
    enabled: bool = True


PluginType = Boefje | Normalizer | Bit
Base64Str = NewType("Base64Str", str)


class EncryptionMiddleware(Enum):
    IDENTITY = "IDENTITY"
    NACL_SEALBOX = "NACL_SEALBOX"
