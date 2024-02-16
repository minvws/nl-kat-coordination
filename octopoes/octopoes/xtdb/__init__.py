from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

# E.g. {'IPPort': {'address': ['IPAddressV6', 'IPAddressV4'] }, ...}
DataModel = dict[str, dict[str, set[str]]]


class FieldSet(Enum):
    ONLY_ID = 0
    ALL_FIELDS = 1


class ForeignKey(BaseModel):
    source_entity: str
    attr_name: str
    related_entities: set[str]
    reverse_name: str


class Datamodel(BaseModel):
    entities: dict[str, list[ForeignKey]]
