from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, NewType, Optional
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field
from pydantic.v1.datetime_parse import parse_datetime

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


def _validate_timezone_aware_datetime(value: datetime) -> datetime:
    parsed = parse_datetime(value)
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError(f"{parsed} is not timezone aware")
    return parsed


class MimeType(BaseModel):
    value: str


class Job(BaseModel):
    id: UUID
    started_at: AwareDatetime
    ended_at: AwareDatetime


class Boefje(BaseModel):
    id: str
    version: Optional[str] = None


class Normalizer(BaseModel):
    id: str
    version: Optional[str] = None


class BoefjeMeta(Job):
    boefje: Boefje
    input_ooi: Optional[str] = None
    arguments: Dict[str, Any]
    organization: str
    runnable_hash: Optional[str] = None
    environment: Optional[Dict[str, str]] = None


class RawDataMeta(BaseModel):
    """Represents only the metadata of a RawData object, without its raw value. Used as an API response model."""

    id: UUID
    boefje_meta: BoefjeMeta
    mime_types: List[MimeType] = Field(default_factory=list)

    # These are set once the raw is saved
    secure_hash: Optional[SecureHash] = None
    signing_provider_url: Optional[str] = None
    hash_retrieval_link: Optional[RetrievalLink] = None


class RawData(BaseModel):
    value: bytes
    boefje_meta: BoefjeMeta
    mime_types: List[MimeType] = Field(default_factory=list)

    # These are set once the raw is saved
    secure_hash: Optional[SecureHash] = None
    signing_provider_url: Optional[str] = None
    hash_retrieval_link: Optional[RetrievalLink] = None


class NormalizerMeta(Job):
    raw_data: RawDataMeta
    normalizer: Normalizer
