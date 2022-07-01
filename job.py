from datetime import datetime, timedelta
from typing import Dict, Optional

from pydantic import BaseModel, Field, validator


class JobException(Exception):
    """General error for jobs"""


class JobImproperKeysException(JobException):
    """Error for jobs missing required keys"""


class JobInvalidJsonException(JobException):
    """Error for jobs missing required keys"""


class Job(BaseModel):
    id: str
    started_at: Optional[datetime] = Field(default=None)
    ended_at: Optional[datetime] = Field(default=None)

    @property
    def runtime(self) -> Optional[timedelta]:
        if self.started_at is not None and self.ended_at is not None:
            return self.ended_at - self.started_at
        else:
            return None


class Boefje(BaseModel):
    id: str
    version: Optional[str] = Field(default=None)

    @validator("id")
    def non_empty_id(cls, value: str):
        if not value:
            raise ValueError("Boefje id cannot be empty")
        return value


class Normalizer(BaseModel):
    name: str  # To be phased out for an id
    version: Optional[str] = Field(default=None)

    @validator("name")
    def non_empty_id(cls, value: str):
        if not value:
            raise ValueError("Normalizer name cannot be empty")
        return value


class BoefjeMeta(Job):
    boefje: Boefje
    input_ooi: str
    arguments: Dict = {}
    organization: str


class NormalizerMeta(Job):
    boefje_meta: BoefjeMeta
    normalizer: Normalizer
