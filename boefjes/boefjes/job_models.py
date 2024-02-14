from datetime import timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints


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


class UnsupportedReturnTypeNormalizer(JobException):
    def __init__(self, result_type: str):
        super().__init__(f"The return type '{result_type}' is not supported")


class InvalidReturnValueNormalizer(JobException):
    def __init__(self, validation_msg: str):
        super().__init__(f"Output dictionary in normalizer was invalid: {validation_msg}")


class NormalizerPlainOOI(BaseModel):  # Validation of plain OOIs being returned from Normalizers
    object_type: str
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class NormalizerObservation(BaseModel):
    type: Literal["observation"] = "observation"
    input_ooi: str
    results: list[NormalizerPlainOOI]


class NormalizerDeclaration(BaseModel):
    type: Literal["declaration"] = "declaration"
    ooi: NormalizerPlainOOI


class NormalizerScanProfile(BaseModel):
    scan_profile_type: str
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class NormalizerResult(BaseModel):  # Moves all validation logic to Pydantic
    item: NormalizerPlainOOI | NormalizerObservation | NormalizerDeclaration | NormalizerScanProfile


class NormalizerOutput(BaseModel):
    observations: list[NormalizerObservation] = []
    declarations: list[NormalizerDeclaration] = []
    scan_profiles: list[NormalizerScanProfile] = []
