from pathlib import Path
from typing import Iterator

import pytest
from sqlalchemy.orm import sessionmaker

from bytes.rabbitmq import RabbitMQEventManager
from bytes.timestamping.rfc3161 import RFC3161HashRepository
from tests.client import BytesAPIClient
from bytes.config import settings, BASE_DIR
from bytes.timestamping.pastebin import PastebinHashRepository
from bytes.timestamping.in_memory import InMemoryHashRepository
from bytes.raw.file_raw_repository import FileRawRepository
from bytes.raw.middleware import NaclBoxMiddleware, IdentityMiddleware
from bytes.repositories.hash_repository import HashRepository
from bytes.sqlalchemy.db import get_engine, SQL_BASE
from bytes.sqlalchemy.sql_meta_repository import SQLMetaDataRepository


@pytest.fixture
def nacl_middleware() -> NaclBoxMiddleware:
    return NaclBoxMiddleware(kat_private=settings.kat_private_key_b64, vws_public=settings.vws_public_key_b64)


@pytest.fixture
def hash_repository() -> HashRepository:
    return PastebinHashRepository(api_dev_key=settings.pastebin_api_dev_key)


@pytest.fixture
def mock_hash_repository(rfc3616_repository: RFC3161HashRepository) -> HashRepository:
    if settings.rfc3161_provider:
        return rfc3616_repository

    return InMemoryHashRepository()


@pytest.fixture
def rfc3616_repository() -> HashRepository:
    assert settings.rfc3161_cert_file and settings.rfc3161_provider

    return RFC3161HashRepository(settings.rfc3161_cert_file.read_bytes(), settings.rfc3161_provider)


@pytest.fixture
def meta_repository(
    raw_repository: FileRawRepository, mock_hash_repository: PastebinHashRepository
) -> Iterator[SQLMetaDataRepository]:
    engine = get_engine()
    session = sessionmaker(bind=engine)()

    SQL_BASE.metadata.create_all(engine)

    yield SQLMetaDataRepository(session, raw_repository, mock_hash_repository, settings)

    session.close()
    session = sessionmaker(bind=engine)()

    for table in SQL_BASE.metadata.tables.keys():
        session.execute(f"TRUNCATE TABLE {table} CASCADE")

    session.commit()
    session.close()


@pytest.fixture
def bytes_api_client() -> Iterator[BytesAPIClient]:
    engine = get_engine()
    SQL_BASE.metadata.create_all(engine)

    yield BytesAPIClient(
        "http://ci_bytes:8000",
        settings.bytes_username,
        settings.bytes_password,
    )

    session = sessionmaker(bind=engine)()
    for table in SQL_BASE.metadata.tables.keys():
        session.execute(f"TRUNCATE TABLE {table} CASCADE")

    session.commit()
    session.close()


@pytest.fixture
def raw_repository(tmp_path: Path) -> FileRawRepository:
    return FileRawRepository(tmp_path, IdentityMiddleware())


@pytest.fixture
def event_manager() -> RabbitMQEventManager:
    return RabbitMQEventManager(settings)
