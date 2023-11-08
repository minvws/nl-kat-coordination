import hashlib
from datetime import timedelta
from typing import Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated


class JobException(Exception):
    """General error for jobs"""

    def __init__(self, message: str):
        super().__init__(message)


class Job(BaseModel):
    id: UUID
    started_at: Optional[AwareDatetime] = Field(default=None)
    ended_at: Optional[AwareDatetime] = Field(default=None)

    @property
    def runtime(self) -> Optional[timedelta]:
        if self.started_at is not None and self.ended_at is not None:
            return self.ended_at - self.started_at
        else:
            return None


class Boefje(BaseModel):
    """Identifier for Boefje in a BoefjeMeta"""

    id: Annotated[str, StringConstraints(min_length=1)]
    version: Optional[str] = Field(default=None)


class Normalizer(BaseModel):
    """Identifier for Normalizer in a NormalizerMeta"""

    id: Annotated[str, StringConstraints(min_length=1)]
    version: Optional[str] = Field(default=None)


class BoefjeMeta(Job):
    boefje: Boefje
    input_ooi: Optional[str] = None
    arguments: Dict = {}
    organization: str
    runnable_hash: Optional[str] = None
    environment: Optional[Dict[str, str]] = None

    @property
    def parameterized_arguments_hash(self) -> str:
        encoded_arguments = ",".join(f"{k}={v}" for k, v in self.arguments.items())

        return hashlib.sha256(encoded_arguments.encode("utf-8")).hexdigest()


class RawDataMeta(BaseModel):
    id: UUID
    boefje_meta: BoefjeMeta
    mime_types: List[Dict[str, str]]


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
    results: List[NormalizerPlainOOI]


class NormalizerDeclaration(BaseModel):
    type: Literal["declaration"] = "declaration"
    ooi: NormalizerPlainOOI


class NormalizerResult(BaseModel):  # Moves all validation logic to Pydantic
    item: Union[NormalizerPlainOOI, NormalizerObservation, NormalizerDeclaration]


class NormalizerOutput(BaseModel):
    observations: List[NormalizerObservation] = []
    declarations: List[NormalizerDeclaration] = []
