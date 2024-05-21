from datetime import timedelta
from typing import Annotated, Literal, TypeAlias
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

from octopoes.models import DeclaredScanProfile, PrimaryKeyToken
from octopoes.models.types import OOIType


class JobException(Exception):
    """General error for jobs"""

    def __init__(self, message: str):
        super().__init__(message)


class Job(BaseModel):
    id: UUID
    started_at: AwareDatetime | None = Field(default=None)
    ended_at: AwareDatetime | None = Field(default=None)

    @property
    def runtime(self) -> timedelta | None:
        if self.started_at is not None and self.ended_at is not None:
            return self.ended_at - self.started_at
        else:
            return None


class Boefje(BaseModel):
    """Identifier for Boefje in a BoefjeMeta"""

    id: Annotated[str, StringConstraints(min_length=1)]
    version: str | None = Field(default=None)


class Normalizer(BaseModel):
    """Identifier for Normalizer in a NormalizerMeta"""

    id: Annotated[str, StringConstraints(min_length=1)]
    version: str | None = Field(default=None)


class BoefjeMeta(Job):
    boefje: Boefje
    input_ooi: str | None = None
    arguments: dict = {}
    organization: str
    runnable_hash: str | None = None
    environment: dict[str, str] | None = None


class RawDataMeta(BaseModel):
    id: UUID
    boefje_meta: BoefjeMeta
    mime_types: list[dict[str, str]]


class NormalizerMeta(Job):
    raw_data: RawDataMeta
    normalizer: Normalizer


class ObservationsWithoutInputOOI(JobException):
    def __init__(self, normalizer_meta: NormalizerMeta):
        super().__init__(
            "Observations are yielded in the normalizer but no input ooi was found. "
            "Your boefje should either yield observations with a custom input"
            "or always run on a specified input ooi type.\n"
            f"NormalizerMeta: {normalizer_meta.model_dump_json(indent=3)}"
        )


class InvalidReturnValueNormalizer(JobException):
    pass


class NormalizerObservation(BaseModel):
    type: Literal["observation"] = "observation"
    input_ooi: str
    results: list[OOIType]


class NormalizerDeclaration(BaseModel):
    type: Literal["declaration"] = "declaration"
    ooi: OOIType


class NormalizerAffirmation(BaseModel):
    type: Literal["affirmation"] = "affirmation"
    ooi: OOIType


class NormalizerResults(BaseModel):
    observations: list[NormalizerObservation] = []
    declarations: list[NormalizerDeclaration] = []
    affirmations: list[NormalizerAffirmation] = []
    scan_profiles: list[DeclaredScanProfile] = []


NormalizerOutput: TypeAlias = OOIType | NormalizerDeclaration | NormalizerAffirmation | DeclaredScanProfile
SerializedOOIValue: TypeAlias = None | str | int | float | dict[str, str | PrimaryKeyToken] | list["SerializedOOIValue"]
SerializedOOI: TypeAlias = dict[str, SerializedOOIValue]
