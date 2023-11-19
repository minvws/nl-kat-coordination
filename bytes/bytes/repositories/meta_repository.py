from typing import Dict, List, Optional, Type
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Query

from bytes.database.db_models import BoefjeMetaInDB, NormalizerMetaInDB, RawFileInDB
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
    limit: Optional[int] = 1
    offset: Optional[int] = 0

    def apply(self, query: Query) -> Query:
        if self.boefje_meta_id:
            query = query.filter(RawFileInDB.boefje_meta_id == str(self.boefje_meta_id))

        if self.organization:
            query = query.join(BoefjeMetaInDB).filter(BoefjeMetaInDB.organization == self.organization)

        if self.normalized:
            query = query.join(NormalizerMetaInDB, isouter=False)

        if self.normalized is False:  # it can also be None, in which case we do not want a filter
            query = query.join(NormalizerMetaInDB, isouter=True).filter(NormalizerMetaInDB.id.is_(None))

        if self.mime_types:
            query = query.filter(RawFileInDB.mime_types.contains([m.value for m in self.mime_types]))

        return query.offset(self.offset).limit(self.limit)


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

    def get_raw_file_count_per_mime_type(self, query_filter: RawDataFilter) -> Dict[str, int]:
        raise NotImplementedError()

    def get_raw_meta_by_id(self, raw_id: UUID) -> RawDataMeta:
        raise NotImplementedError()
