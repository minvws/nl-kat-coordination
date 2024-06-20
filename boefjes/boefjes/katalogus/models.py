import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Organisation(BaseModel):
    id: str
    name: str


class Plugin(BaseModel):
    id: str
    name: str | None = None
    version: str | None = None
    created: datetime.datetime | None = None
    description: str | None = None
    environment_keys: list[str] = Field(default_factory=list)
    enabled: bool = False
    static: bool = True  # We need to differentiate between local and remote plugins to know which ones can be deleted

    def __str__(self):
        return f"{self.id}:{self.version}"


class Boefje(Plugin):
    type: Literal["boefje"] = "boefje"
    scan_level: int = 1
    consumes: set[str] = Field(default_factory=set)
    produces: set[str] = Field(default_factory=set)
    runnable_hash: str | None = None
    oci_image: str | None = None
    oci_arguments: list[str] = Field(default_factory=list)


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


class EncryptionMiddleware(Enum):
    IDENTITY = "IDENTITY"
    NACL_SEALBOX = "NACL_SEALBOX"


class PaginationParameters(BaseModel):
    offset: int = 0
    limit: int | None = None


class FilterParameters(BaseModel):
    q: str | None = None
    type: Literal["boefje", "normalizer", "bit"] | None = None
    ids: list[str] | None = None
    state: bool | None = None
    scan_level: int = 0
