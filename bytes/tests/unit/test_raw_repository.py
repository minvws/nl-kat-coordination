import uuid

import pytest
from pydantic import ValidationError

from bytes.config import get_settings
from bytes.raw.file_raw_repository import FileRawRepository
from bytes.raw.middleware import NaclBoxMiddleware
from bytes.repositories.meta_repository import RawDataFilter
from tests.loading import get_raw_data


def has_encryption_keys() -> bool:
    settings = get_settings()

    return settings.private_key_b64 and settings.public_key_b64


def test_save_raw(raw_repository: FileRawRepository) -> None:
    raw_data = get_raw_data()
    raw_id = str(uuid.uuid4())
    raw_repository.save_raw(raw_id, raw_data)
    retrieved_raw = raw_repository.get_raw(raw_id, raw_data.boefje_meta)

    assert retrieved_raw.value == b"KAT for president"


@pytest.mark.skipif("not has_encryption_keys()")
def test_nacl_middleware(nacl_middleware: NaclBoxMiddleware) -> None:
    msg = b"The president is taking the underpass"

    encrypted = nacl_middleware.encode(contents=msg)
    decrypted = nacl_middleware.decode(contents=encrypted)

    assert encrypted != msg
    assert decrypted == msg


def test_filter_validator() -> None:
    with pytest.raises(ValidationError):
        RawDataFilter()

    RawDataFilter(organization="Not None")
    RawDataFilter(boefje_meta_id="3a9f1b33-f703-4c32-b0ae-44d0473c8aa5")
