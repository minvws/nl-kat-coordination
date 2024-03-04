from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from octopoes.models import Reference


class OriginType(Enum):
    DECLARATION = "declaration"
    OBSERVATION = "observation"
    INFERENCE = "inference"
    AFFIRMATION = "affirmation"


class Origin(BaseModel):
    origin_type: OriginType
    method: str
    source: Reference
    result: list[Reference] = Field(default_factory=list)
    task_id: UUID | None = None

    def __sub__(self, other) -> set[Reference]:
        if isinstance(other, Origin):
            return set(self.result) - set(other.result)
        else:
            return NotImplemented

    @property
    def id(self) -> str:
        return f"{self.__class__.__name__}|{self.origin_type.value}|{self.method}|{self.source}"

    def __eq__(self, other):
        if isinstance(other, Origin):
            return (
                self.origin_type == other.origin_type
                and self.method == other.method
                and self.source == other.source
                and set(self.result) == set(other.result)
            )
        return False


class OriginParameter(BaseModel):
    origin_id: str
    reference: Reference

    @property
    def id(self) -> str:
        return f"{self.__class__.__name__}|{self.origin_id}|{self.reference}"
