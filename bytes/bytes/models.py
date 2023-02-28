from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Iterable, Callable, Union, Optional, Dict, Any, NewType, List

from pydantic import BaseModel, Field
from pydantic.datetime_parse import parse_datetime, StrBytesIntFloat

RetrievalLink = NewType("RetrievalLink", str)
SecureHash = NewType("SecureHash", str)


class EncryptionMiddleware(str, Enum):
    IDENTITY = "IDENTITY"
    NACL_SEALBOX = "NACL_SEALBOX"


class HashingAlgorithm(str, Enum):
    SHA512 = "sha512"
    SHA224 = "sha224"


class HashingRepositoryReference(str, Enum):
    IN_MEMORY = "IN_MEMORY"
    PASTEBIN = "PASTEBIN"
    RFC3161 = "RFC3161"


class TimezoneAwareDatetime(datetime):
    @classmethod
    def __get_validators__(cls) -> Iterable[Callable[[Union[datetime, StrBytesIntFloat]], datetime]]:
        yield cls.validate

    @classmethod
    def validate(cls, value: Union[datetime, StrBytesIntFloat]) -> datetime:
        parsed = parse_datetime(value)
        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            raise ValueError(f"{parsed} is not timezone aware")
        return parsed


class MimeType(BaseModel):
    value: str


class Job(BaseModel):
    id: str
    started_at: TimezoneAwareDatetime
    ended_at: TimezoneAwareDatetime


class Boefje(BaseModel):
    id: str
    version: Optional[str]


class Normalizer(BaseModel):
    id: str
    version: Optional[str]


class BoefjeMeta(Job):
    boefje: Boefje
    input_ooi: Optional[str]
    arguments: Dict[str, Any]
    organization: str


class RawDataMeta(BaseModel):
    """Represents only the metadata of a RawData object, without its raw value. Used as an API response model."""

    id: str
    boefje_meta: BoefjeMeta
    mime_types: List[MimeType] = Field(default_factory=list)

    # These are set once the raw is saved
    secure_hash: Optional[SecureHash]
    hash_retrieval_link: Optional[RetrievalLink]


class RawData(BaseModel):
    value: bytes
    boefje_meta: BoefjeMeta
    mime_types: List[MimeType] = Field(default_factory=list)

    # These are set once the raw is saved
    secure_hash: Optional[SecureHash]
    hash_retrieval_link: Optional[RetrievalLink]


class NormalizerMeta(Job):
    raw_file_id: Optional[str]
    boefje_meta: BoefjeMeta  # To be phased out?
    normalizer: Normalizer
