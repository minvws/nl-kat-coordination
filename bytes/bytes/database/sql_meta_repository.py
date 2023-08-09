import logging
import uuid
from typing import Dict, Iterator, List, Optional, Type

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from bytes.config import Settings, get_settings
from bytes.database.db import SQL_BASE, get_engine
from bytes.database.db_models import BoefjeMetaInDB, NormalizerMetaInDB, RawFileInDB, SigningProviderInDB
from bytes.models import (
    Boefje,
    BoefjeMeta,
    MimeType,
    Normalizer,
    NormalizerMeta,
    RawData,
    RawDataMeta,
)
from bytes.raw.file_raw_repository import create_raw_repository
from bytes.repositories.hash_repository import HashRepository
from bytes.repositories.meta_repository import BoefjeMetaFilter, MetaDataRepository, NormalizerMetaFilter, RawDataFilter
from bytes.repositories.raw_repository import RawRepository
from bytes.timestamping.hashing import hash_data
from bytes.timestamping.provider import create_hash_repository

logger = logging.getLogger(__name__)


class SQLMetaDataRepository(MetaDataRepository):
    def __init__(
        self, session: Session, raw_repository: RawRepository, hash_repository: HashRepository, app_settings: Settings
    ):
        self.session = session
        self.raw_repository = raw_repository
        self.hash_repository = hash_repository
        self.app_settings = app_settings

    def __enter__(self) -> None:
        pass

    def __exit__(self, _exc_type: Type[Exception], _exc_value: str, _exc_traceback: str) -> None:
        try:
            self.session.commit()
            logger.debug("Committed session")
        except IntegrityError as e:
            logger.exception("An integrity error occurred while committing a session.")

            raise MetaIntegrityError(str(e)) from e

    def save_boefje_meta(self, boefje_meta: BoefjeMeta) -> None:
        boefje_meta_in_db = to_boefje_meta_in_db(boefje_meta)
        self.session.add(boefje_meta_in_db)

        logger.info("Added boefje meta [id=%s]", boefje_meta.id)

    def get_boefje_meta_by_id(self, boefje_meta_id: str) -> BoefjeMeta:
        boefje_meta_in_db = self.session.get(BoefjeMetaInDB, boefje_meta_id)

        if boefje_meta_in_db is None:
            raise ObjectNotFoundException(BoefjeMetaInDB, id=boefje_meta_id)

        return to_boefje_meta(boefje_meta_in_db)

    def get_boefje_meta(self, query_filter: BoefjeMetaFilter) -> List[BoefjeMeta]:
        logger.debug("Querying boefje meta: %s", query_filter.json())

        query = self.session.query(BoefjeMetaInDB).filter(BoefjeMetaInDB.organization == query_filter.organization)

        if query_filter.boefje_id is not None:
            query = query.filter(BoefjeMetaInDB.boefje_id == query_filter.boefje_id)

        if query_filter.input_ooi != "*":
            query = query.filter(BoefjeMetaInDB.input_ooi == query_filter.input_ooi)

        ordering_fn = BoefjeMetaInDB.started_at.desc if query_filter.descending else BoefjeMetaInDB.started_at.asc
        query = query.order_by(ordering_fn()).offset(query_filter.offset).limit(query_filter.limit)

        return [to_boefje_meta(boefje_meta) for boefje_meta in query]

    def save_normalizer_meta(self, normalizer_meta: NormalizerMeta) -> None:
        normalizer_meta_in_db = to_normalizer_meta_in_db(normalizer_meta)
        self.session.add(normalizer_meta_in_db)

        logger.info("Added normalizer meta [id=%s]", normalizer_meta.id)

    def get_normalizer_meta_by_id(self, normalizer_meta_id: str) -> NormalizerMeta:
        normalizer_meta_in_db = self.session.get(NormalizerMetaInDB, normalizer_meta_id)

        if normalizer_meta_in_db is None:
            raise ObjectNotFoundException(NormalizerMetaInDB, id=normalizer_meta_id)

        return to_normalizer_meta(normalizer_meta_in_db)

    def get_normalizer_meta(self, query_filter: NormalizerMetaFilter) -> List[NormalizerMeta]:
        logger.debug("Querying normalizer meta: %s", query_filter.json())

        if query_filter.raw_id is not None:
            query = self.session.query(NormalizerMetaInDB).filter(NormalizerMetaInDB.raw_file_id == query_filter.raw_id)
        else:
            query = (
                self.session.query(NormalizerMetaInDB)
                .join(RawFileInDB)
                .join(BoefjeMetaInDB)
                .filter(RawFileInDB.boefje_meta_id == BoefjeMetaInDB.id)
                .filter(BoefjeMetaInDB.organization == query_filter.organization)
            )

        if query_filter.normalizer_id is not None:
            query = query.filter(NormalizerMetaInDB.normalizer_id == query_filter.normalizer_id)

        ordering_fn = (
            NormalizerMetaInDB.started_at.desc if query_filter.descending else NormalizerMetaInDB.started_at.asc
        )
        query = query.order_by(ordering_fn()).offset(query_filter.offset).limit(query_filter.limit)

        return [to_normalizer_meta(normalizer_meta) for normalizer_meta in query]

    def save_raw(self, raw: RawData) -> str:
        # Hash the data
        secure_hash = hash_data(raw, raw.boefje_meta.ended_at, self.app_settings.hashing_algorithm)

        # Send hash to a third party service.
        link = self.hash_repository.store(secure_hash=secure_hash)

        raw.signing_provider_url = self.hash_repository.get_signing_provider_url()
        raw.secure_hash = secure_hash
        raw.hash_retrieval_link = link

        logger.info("Added hash %s and link %s to data", secure_hash, link)

        signing_provider = self._get_or_create_signing_provider(raw.signing_provider_url)
        raw_file_in_db = to_raw_file_in_db(raw, signing_provider if signing_provider else None)

        self.session.add(raw_file_in_db)
        self.raw_repository.save_raw(raw_file_in_db.id, raw)
        logger.info("Added raw data [id=%s]", raw_file_in_db.id)

        return str(raw_file_in_db.id)

    def get_raw(self, query_filter: RawDataFilter) -> List[RawDataMeta]:
        logger.debug("Querying raw data: %s", query_filter.json())

        if query_filter.boefje_meta_id:
            query = self.session.query(RawFileInDB).filter(RawFileInDB.boefje_meta_id == query_filter.boefje_meta_id)
        else:
            query = (
                self.session.query(RawFileInDB)
                .join(BoefjeMetaInDB)
                .filter(BoefjeMetaInDB.organization == query_filter.organization)
            )

        if query_filter.normalized:
            query = query.join(NormalizerMetaInDB, isouter=False)

        if query_filter.normalized is False:  # it can also be None, in which case we do not want a filter
            query = query.join(NormalizerMetaInDB, isouter=True).filter(NormalizerMetaInDB.id.is_(None))

        if query_filter.mime_types:
            query = query.filter(RawFileInDB.mime_types.contains([m.value for m in query_filter.mime_types]))

        query = query.offset(query_filter.offset).limit(query_filter.limit)

        return [to_raw_meta(raw_file_in_db) for raw_file_in_db in query]

    def get_raw_by_id(self, raw_id: str) -> RawData:
        raw_in_db: Optional[RawFileInDB] = self.session.get(RawFileInDB, raw_id)

        if raw_in_db is None:
            raise ObjectNotFoundException(RawFileInDB, id=raw_id)

        boefje_meta = to_boefje_meta(raw_in_db.boefje_meta)
        return self.raw_repository.get_raw(raw_in_db.id, boefje_meta)

    def has_raw(self, boefje_meta: BoefjeMeta, mime_types: List[MimeType]) -> bool:
        query = self.session.query(RawFileInDB).filter(RawFileInDB.boefje_meta_id == boefje_meta.id)

        if len(mime_types) > 0:
            query = query.filter(RawFileInDB.mime_types.contains([mime_type.value for mime_type in mime_types]))

        count: int = query.count()

        return count > 0

    def get_raw_file_count_per_organization(self) -> Dict[str, int]:
        query = (
            self.session.query(BoefjeMetaInDB.organization, func.count())
            .join(RawFileInDB)
            .group_by(BoefjeMetaInDB.organization)
        )

        return {organization_id: count for organization_id, count in query}

    def _to_raw(self, raw_file_in_db: RawFileInDB) -> RawData:
        boefje_meta = to_boefje_meta(raw_file_in_db.boefje_meta)
        data = self.raw_repository.get_raw(raw_file_in_db.id, boefje_meta)

        return to_raw_data(raw_file_in_db, data.value)

    def _get_or_create_signing_provider(self, signing_provider_url: Optional[str]) -> Optional[SigningProviderInDB]:
        if not signing_provider_url:
            return None

        query = self.session.query(SigningProviderInDB).filter(SigningProviderInDB.url == signing_provider_url)
        signing_provider = query.first()

        if not signing_provider:
            signing_provider = SigningProviderInDB(url=signing_provider_url)
            self.session.add(signing_provider)

        return signing_provider


def create_meta_data_repository() -> Iterator[MetaDataRepository]:
    settings = get_settings()

    session = sessionmaker(bind=get_engine(settings.bytes_db_uri))()
    repository = SQLMetaDataRepository(
        session, create_raw_repository(settings), create_hash_repository(settings), settings
    )

    try:
        yield repository
    except Exception as error:
        logger.exception("An error occurred during the session.")
        session.rollback()
        logger.warning("Rolled back session.")

        raise error
    finally:
        session.close()
        logger.debug("Closed session")


class ObjectNotFoundException(Exception):
    def __init__(self, cls: Type[SQL_BASE], **kwargs):  # type: ignore
        super().__init__(f"The object of type {cls} was not found for query parameters {kwargs}")


class MetaIntegrityError(Exception):
    """An IntegrityError occurred for the MetaRepository"""


def to_boefje_meta_in_db(boefje_meta: BoefjeMeta) -> BoefjeMetaInDB:
    return BoefjeMetaInDB(
        id=boefje_meta.id,
        boefje_id=boefje_meta.boefje.id,
        boefje_version=boefje_meta.boefje.version,
        arguments=boefje_meta.arguments,
        input_ooi=boefje_meta.input_ooi,
        organization=boefje_meta.organization,
        started_at=boefje_meta.started_at,
        ended_at=boefje_meta.ended_at,
        runnable_hash=boefje_meta.runnable_hash,
        environment=boefje_meta.environment,
    )


def to_boefje_meta(boefje_meta_in_db: BoefjeMetaInDB) -> BoefjeMeta:
    return BoefjeMeta(
        id=boefje_meta_in_db.id,
        boefje=Boefje(id=boefje_meta_in_db.boefje_id, version=boefje_meta_in_db.boefje_version),
        arguments=boefje_meta_in_db.arguments,
        input_ooi=boefje_meta_in_db.input_ooi,
        organization=boefje_meta_in_db.organization,
        started_at=boefje_meta_in_db.started_at,
        ended_at=boefje_meta_in_db.ended_at,
        runnable_hash=boefje_meta_in_db.runnable_hash,
        environment=boefje_meta_in_db.environment,
    )


def to_normalizer_meta_in_db(normalizer_meta: NormalizerMeta) -> NormalizerMetaInDB:
    return NormalizerMetaInDB(
        id=normalizer_meta.id,
        normalizer_id=normalizer_meta.normalizer.id,
        normalizer_version=normalizer_meta.normalizer.version,
        started_at=normalizer_meta.started_at,
        ended_at=normalizer_meta.ended_at,
        raw_file_id=normalizer_meta.raw_data.id,
    )


def to_normalizer_meta(normalizer_meta_in_db: NormalizerMetaInDB) -> NormalizerMeta:
    raw_meta = to_raw_meta(normalizer_meta_in_db.raw_file)

    return NormalizerMeta(
        id=normalizer_meta_in_db.id,
        normalizer=Normalizer(
            id=normalizer_meta_in_db.normalizer_id,
            version=normalizer_meta_in_db.normalizer_version,
        ),
        started_at=normalizer_meta_in_db.started_at,
        ended_at=normalizer_meta_in_db.ended_at,
        raw_data=raw_meta,
    )


def to_raw_file_in_db(raw_data: RawData, signing_provider: Optional[SigningProviderInDB]) -> RawFileInDB:
    return RawFileInDB(
        id=str(uuid.uuid4()),
        boefje_meta_id=raw_data.boefje_meta.id,
        secure_hash=raw_data.secure_hash,
        signing_provider=signing_provider if signing_provider else None,
        hash_retrieval_link=raw_data.hash_retrieval_link,
        mime_types=[mime_type.value for mime_type in raw_data.mime_types],
    )


def raw_meta_to_raw_file_in_db(raw_data_meta: RawDataMeta, signing_provider_id: Optional[int]) -> RawFileInDB:
    return RawFileInDB(
        id=raw_data_meta.id,
        boefje_meta_id=raw_data_meta.boefje_meta.id,
        secure_hash=raw_data_meta.secure_hash,
        signing_provider_id=signing_provider_id if signing_provider_id else None,
        hash_retrieval_link=raw_data_meta.hash_retrieval_link,
        mime_types=[mime_type.value for mime_type in raw_data_meta.mime_types],
    )


def to_raw_data(raw_file_in_db: RawFileInDB, raw: bytes) -> RawData:
    return RawData(
        value=raw,
        boefje_meta=to_boefje_meta(raw_file_in_db.boefje_meta),
        secure_hash=raw_file_in_db.secure_hash,
        signing_provider_url=raw_file_in_db.signing_provider.url if raw_file_in_db.signing_provider else None,
        hash_retrieval_link=raw_file_in_db.hash_retrieval_link,
        mime_types=[to_mime_type(mime_type) for mime_type in raw_file_in_db.mime_types],
    )


def to_raw_meta(raw_file_in_db: RawFileInDB) -> RawDataMeta:
    return RawDataMeta(
        id=raw_file_in_db.id,
        boefje_meta=to_boefje_meta(raw_file_in_db.boefje_meta),
        secure_hash=raw_file_in_db.secure_hash,
        signing_provider_url=raw_file_in_db.signing_provider.url if raw_file_in_db.signing_provider else None,
        hash_retrieval_link=raw_file_in_db.hash_retrieval_link,
        mime_types=[to_mime_type(mime_type) for mime_type in raw_file_in_db.mime_types],
    )


def to_mime_type(mime_type: str) -> MimeType:
    return MimeType(value=mime_type)
