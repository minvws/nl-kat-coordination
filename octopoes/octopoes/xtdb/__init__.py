from __future__ import annotations

from enum import Enum
from typing import Dict, Set, List

from pydantic import BaseModel

# E.g. {'IPPort': {'address': ['IPAddressV6', 'IPAddressV4'] }, ...}
DataModel = Dict[str, Dict[str, Set[str]]]


class FieldSet(Enum):
    ONLY_ID = 0
    ALL_FIELDS = 1


class ForeignKey(BaseModel):
    source_entity: str
    attr_name: str
    related_entities: Set[str]
    reverse_name: str


class Datamodel(BaseModel):
    entities: Dict[str, List[ForeignKey]]
