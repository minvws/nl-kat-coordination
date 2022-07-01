import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Literal, Dict, Union

from pydantic import BaseModel, Field


class PluginChoice(Enum):  # TODO: shouldn't this be the 'type' field on plugins?
    BOEFJE = "boefje"
    NORMALIZER = "normalizer"
    BIT = "bit"


class Plugin(BaseModel):
    id: str
    name: Optional[str]
    version: Optional[str]
    authors: Optional[List[str]]
    created: Optional[datetime.datetime]
    environment_keys: Optional[List[str]]
    related: Optional[List[str]]
    description: str = ""

    def __str__(self):
        return self.id


class Boefje(Plugin):
    type: Literal["boefje"] = "boefje"
    scan_level: int = 1
    consumes: str
    options: Optional[List[str]]
    produces: List[str]  # mime types


class Normalizer(Plugin):
    type: Literal["normalizer"] = "normalizer"
    consumes: List[str]  # mime types (and/ or boefjes)
    produces: List[str]  # oois


class Bit(Plugin):
    type: Literal["bit"] = "bit"
    consumes: str
    produces: List[str]
    parameters: List[str]  # ooi.relation-name


PluginType = Union[Boefje, Normalizer, Bit]

_FTYPE_MAPPING = {
    ".squashfs": "squashfs",
    ".vcdiff": "squashfs.vcdiff",
    ".qcow2": "disk-kvm.img",
}


class File(BaseModel):
    location: Path
    size: int
    hash: Optional[str]

    @property
    def ftype(self) -> str:
        name, suffix = self.location.name, self.location.suffix

        return _FTYPE_MAPPING.get(suffix, _FTYPE_MAPPING.get(name, name))


class CombinedFile(File):
    combined_rootxz_sha256: Optional[str]
    combined_squashfs_sha256: Optional[str]
    combined_disk_vm_img_sha256: Optional[str]


class Image(BaseModel):
    plugin: PluginType
    location: Path
    metadata: Dict = Field(default_factory=dict)
    files: List[File] = Field(default_factory=list)

    @property
    def alias(self) -> str:
        return f"{self.plugin.id}/{self.plugin.version}"

    @property
    def aliases(self) -> List[str]:
        aliases = [self.alias]

        properties: Optional[Dict[str, str]] = self.metadata.get("properties")
        if properties is not None:
            architecture = properties.get("architecture")
            if architecture is not None:
                # todo: use mapped architecture?
                self.aliases.append(f"{self.alias}/{architecture}")

        return aliases

    @property
    def architecture(self) -> Optional[str]:
        properties: Optional[Dict[str, str]] = self.metadata.get("properties")
        if properties is None:
            return None

        return properties.get("architecture")

    def __str__(self):
        return f"{self.plugin.id}"


class Index(BaseModel):
    images: Dict[str, Image] = Field(default_factory=dict)
