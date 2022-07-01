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


class OOIDBEvent(DBEvent):
    entity_type: Literal["ooi"] = "ooi"
    old_data: Optional[OOIType]
    new_data: Optional[OOIType]


class OriginDBEvent(DBEvent):
    entity_type: Literal["origin"] = "origin"
    old_data: Optional[Origin]
    new_data: Optional[Origin]


class OriginParameterDBEvent(DBEvent):
    entity_type: Literal["origin_parameter"] = "origin_parameter"
    old_data: Optional[OriginParameter]
    new_data: Optional[OriginParameter]


class ScanProfileDBEvent(DBEvent):
    entity_type: Literal["scan_profile"] = "scan_profile"
    old_data: Optional[ScanProfile]
    new_data: Optional[ScanProfile]


EVENT_TYPE = Union[OOIDBEvent, OriginDBEvent, OriginParameterDBEvent, ScanProfileDBEvent]


class CalculateScanLevelTask(BaseModel):
    reference: Reference
    valid_time: datetime
    client: str
