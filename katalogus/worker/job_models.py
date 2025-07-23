import uuid
from datetime import timedelta
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from .models import Boefje, Normalizer


class JobException(Exception):
    """General error for jobs"""

    def __init__(self, message: str):
        super().__init__(message)


class BoefjeMeta(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    boefje: Boefje
    input_ooi: str | None = None
    input_ooi_data: dict = Field(default_factory=dict)
    organization: str
    runnable_hash: str | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    started_at: AwareDatetime | None = Field(default=None)
    ended_at: AwareDatetime | None = Field(default=None)

    @property
    def runtime(self) -> timedelta | None:
        if self.started_at is not None and self.ended_at is not None:
            return self.ended_at - self.started_at
        else:
            return None


class RawData(BaseModel):
    id: int
    boefje_meta: BoefjeMeta
    type: str


class NormalizerMeta(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    raw_data: RawData
    normalizer: Normalizer
    started_at: AwareDatetime | None = Field(default=None)
    ended_at: AwareDatetime | None = Field(default=None)

    @property
    def runtime(self) -> timedelta | None:
        if self.started_at is not None and self.ended_at is not None:
            return self.ended_at - self.started_at
        else:
            return None


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
