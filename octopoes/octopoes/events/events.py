from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from octopoes.models import Reference, ScanProfile
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
    client: str | None = None

    @property
    def primary_key(self) -> str:
        return ""


class OOIDBEvent(DBEvent):
    entity_type: Literal["ooi"] = "ooi"
    old_data: OOIType | None = None
    new_data: OOIType | None = None

    @property
    def primary_key(self) -> str:
        return self.new_data.primary_key if self.new_data else self.old_data.primary_key


class OriginDBEvent(DBEvent):
    entity_type: Literal["origin"] = "origin"
    old_data: Origin | None = None
    new_data: Origin | None = None

    @property
    def primary_key(self) -> str:
        return self.new_data.id if self.new_data else self.old_data.id


class OriginParameterDBEvent(DBEvent):
    entity_type: Literal["origin_parameter"] = "origin_parameter"
    old_data: OriginParameter | None = None
    new_data: OriginParameter | None = None

    @property
    def primary_key(self) -> str:
        return self.new_data.id if self.new_data else self.old_data.id


class ScanProfileDBEvent(DBEvent):
    entity_type: Literal["scan_profile"] = "scan_profile"
    reference: Reference
    old_data: ScanProfile | None = None
    new_data: ScanProfile | None = None

    @property
    def primary_key(self) -> Reference:
        return self.reference


DBEventType = Annotated[
    OOIDBEvent | OriginDBEvent | OriginParameterDBEvent | ScanProfileDBEvent, Field(discriminator="entity_type")
]
