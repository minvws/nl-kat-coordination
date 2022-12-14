from datetime import datetime
from enum import Enum
from typing import Optional, Union, Literal

from pydantic import BaseModel

from octopoes.models import ScanProfile, Reference
from octopoes.models.origin import Origin, OriginParameter
from octopoes.models.types import OOIType


class OperationType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class DBEvent(BaseModel):
    entity_type: str
    operation_type: OperationType
    valid_time: datetime
    client: Optional[str]

    @property
    def primary_key(self) -> str:
        return ""


class OOIDBEvent(DBEvent):
    entity_type: Literal["ooi"] = "ooi"
    old_data: Optional[OOIType]
    new_data: Optional[OOIType]

    @property
    def primary_key(self) -> str:
        return self.new_data.primary_key if self.new_data else self.old_data.primary_key


class OriginDBEvent(DBEvent):
    entity_type: Literal["origin"] = "origin"
    old_data: Optional[Origin]
    new_data: Optional[Origin]

    @property
    def primary_key(self) -> str:
        return self.new_data.id if self.new_data else self.old_data.id


class OriginParameterDBEvent(DBEvent):
    entity_type: Literal["origin_parameter"] = "origin_parameter"
    old_data: Optional[OriginParameter]
    new_data: Optional[OriginParameter]

    @property
    def primary_key(self) -> str:
        return self.new_data.id if self.new_data else self.old_data.id


class ScanProfileDBEvent(DBEvent):
    entity_type: Literal["scan_profile"] = "scan_profile"
    old_data: Optional[ScanProfile]
    new_data: Optional[ScanProfile]

    @property
    def primary_key(self) -> Reference:
        return self.new_data.reference if self.new_data else self.old_data.reference


EVENT_TYPE = Union[OOIDBEvent, OriginDBEvent, OriginParameterDBEvent, ScanProfileDBEvent]
