from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from pydantic import BaseModel, Field, root_validator

from bytes.models import BoefjeMeta, MimeType, NormalizerMeta, RawData, RawDataMeta


class BoefjeMetaFilter(BaseModel):
    organization: str

    boefje_id: Optional[str]
    input_ooi: Optional[str] = "*"
    limit: int = 1
    offset: int = 0
    descending: bool = True


class NormalizerMetaFilter(BaseModel):
    organization: Optional[str]
    normalizer_id: Optional[str]
    raw_id: Optional[UUID]
    limit: int = 1
    offset: int = 0
    descending: bool = True


class RawDataFilter(BaseModel):
    organization: Optional[str]
    boefje_meta_id: Optional[UUID]
    normalized: Optional[bool]
    mime_types: List[MimeType] = Field(default_factory=list)
    limit: int = 1
    offset: int = 0

    @root_validator(pre=False)
    def either_organization_or_boefje_meta_id(  # pylint: disable=no-self-argument
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if values.get("organization") or values.get("boefje_meta_id"):
            return values

        raise ValueError("boefje_meta_id and organization cannot both be None.")


class MetaDataRepository:
    def __enter__(self) -> None:
        pass

    def __exit__(self, _exc_type: Type[Exception], _exc_value: str, _exc_traceback: str) -> None:
        pass

    def save_boefje_meta(self, boefje_meta: BoefjeMeta) -> None:
        raise NotImplementedError()

    def get_boefje_meta_by_id(self, boefje_meta_id: UUID) -> BoefjeMeta:
        raise NotImplementedError()

    def get_boefje_meta(self, query_filter: BoefjeMetaFilter) -> List[BoefjeMeta]:
        raise NotImplementedError()

    def save_normalizer_meta(self, normalizer_meta: NormalizerMeta) -> None:
        raise NotImplementedError()

    def get_normalizer_meta_by_id(self, normalizer_meta_id: UUID) -> NormalizerMeta:
        raise NotImplementedError()

    def get_normalizer_meta(self, query_filter: NormalizerMetaFilter) -> List[NormalizerMeta]:
        raise NotImplementedError()

    def save_raw(self, raw: RawData) -> UUID:
        raise NotImplementedError()

    def get_raw_by_id(self, raw_id: UUID) -> RawData:
        raise NotImplementedError()

    def get_raw(self, query_filter: RawDataFilter) -> List[RawDataMeta]:
        raise NotImplementedError()

    def has_raw(self, boefje_meta: BoefjeMeta, mime_types: List[MimeType]) -> bool:
        raise NotImplementedError()

    def get_raw_file_count_per_organization(self) -> Dict[str, int]:
        raise NotImplementedError()

    def get_raw_meta_by_id(self, raw_id: UUID) -> RawDataMeta:
        raise NotImplementedError()
