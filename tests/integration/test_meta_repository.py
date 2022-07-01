import uuid
from datetime import timedelta

from bytes.models import RetrievalLink, SecureHash, MimeType
from bytes.repositories.meta_repository import BoefjeMetaFilter, RawDataFilter
from bytes.sqlalchemy.sql_meta_repository import SQLMetaDataRepository
from tests.loading import get_boefje_meta, get_normalizer_meta, get_raw_data


def test_save_boefje_meta(meta_repository: SQLMetaDataRepository) -> None:
    boefje_meta = get_boefje_meta()
    second_boefje_meta = get_boefje_meta(
        str(uuid.uuid4()), boefje_id=boefje_meta.boefje.id, input_ooi="Network|internet"
    )
    third_boefje_meta = get_boefje_meta(str(uuid.uuid4()), boefje_id="kat-test-2", input_ooi=boefje_meta.input_ooi)

    second_boefje_meta.started_at = boefje_meta.started_at + timedelta(hours=5)
    third_boefje_meta.started_at = boefje_meta.started_at - timedelta(hours=5)

    with meta_repository:
        meta_repository.save_boefje_meta(boefje_meta)
        meta_repository.save_boefje_meta(second_boefje_meta)
        meta_repository.save_boefje_meta(third_boefje_meta)

    boefje_meta_from_db = meta_repository.get_boefje_meta_by_id(boefje_meta.id)
    assert boefje_meta == boefje_meta_from_db

    first_and_second = meta_repository.get_boefje_meta(
        BoefjeMetaFilter(
            organization=boefje_meta.organization, boefje_id=boefje_meta.boefje.id, limit=3, descending=False
        )
    )
    assert len(first_and_second) == 2

    assert boefje_meta == first_and_second[0]
    assert second_boefje_meta == first_and_second[1]

    second_and_first = meta_repository.get_boefje_meta(
        BoefjeMetaFilter(organization=boefje_meta.organization, boefje_id=boefje_meta.boefje.id, limit=3)
    )
    assert len(second_and_first) == 2

    assert boefje_meta == second_and_first[1]
    assert second_boefje_meta == second_and_first[0]

    first_and_third = meta_repository.get_boefje_meta(
        BoefjeMetaFilter(organization=boefje_meta.organization, input_ooi=boefje_meta.input_ooi, limit=3)
    )
    assert len(first_and_third) == 2

    assert boefje_meta == first_and_third[0]
    assert third_boefje_meta == first_and_third[1]

    third = meta_repository.get_boefje_meta(
        BoefjeMetaFilter(organization=boefje_meta.organization, input_ooi=boefje_meta.input_ooi, descending=False)
    )
    assert third_boefje_meta == third[0]

    wrong_organization = meta_repository.get_boefje_meta(
        BoefjeMetaFilter(organization="test2", input_ooi=boefje_meta.input_ooi, descending=False)
    )
    assert wrong_organization == []


def test_save_boefje_meta_hash(meta_repository: SQLMetaDataRepository) -> None:
    raw = get_raw_data()
    link = RetrievalLink("abcd.com")
    sec_hash = SecureHash("123456")

    with meta_repository:
        meta_repository.save_boefje_meta(raw.boefje_meta)

    raw.hash_retrieval_link = link
    raw.secure_hash = sec_hash
    raw.mime_types = [MimeType(value="text/plain")]

    with meta_repository:
        raw_id = meta_repository.save_raw(raw)

    query_filter = RawDataFilter(
        organization=raw.boefje_meta.organization, boefje_meta_id=raw.boefje_meta.id, normalized=False
    )
    first_updated_raw = meta_repository.get_raws(query_filter).pop()
    assert "hash_retrieval_link" in first_updated_raw.json()
    assert "secure_hash" in first_updated_raw.json()

    query_filter = RawDataFilter(
        organization=raw.boefje_meta.organization,
        boefje_meta_id=raw.boefje_meta.id,
        mime_types=[MimeType(value="text/plain")],
    )
    first_updated_raw = meta_repository.get_raws(query_filter).pop()
    assert "hash_retrieval_link" in first_updated_raw.json()
    assert "secure_hash" in first_updated_raw.json()

    query_filter = RawDataFilter(
        organization=raw.boefje_meta.organization,
        boefje_meta_id=raw.boefje_meta.id,
        mime_types=[MimeType(value="bad/mime")],
    )
    empty_raws = meta_repository.get_raws(query_filter)
    assert empty_raws == []

    # No raw data has been normalized
    query_filter = RawDataFilter(organization=raw.boefje_meta.organization, normalized=True)
    empty_raws = meta_repository.get_raws(query_filter)
    assert empty_raws == []

    with meta_repository:
        meta_repository.save_normalizer_meta(get_normalizer_meta(raw_id))

    # Now the raw data has been normalized
    non_empty_raws = meta_repository.get_raws(query_filter)
    assert len(non_empty_raws) == 1


def test_save_normalizer_meta(meta_repository: SQLMetaDataRepository) -> None:
    normalizer_meta = get_normalizer_meta()

    with meta_repository:
        meta_repository.save_boefje_meta(normalizer_meta.boefje_meta)
        meta_repository.save_normalizer_meta(normalizer_meta)

    normalizer_meta_from_db = meta_repository.get_normalizer_meta(normalizer_meta.id)
    boefje_meta_from_db = meta_repository.get_boefje_meta_by_id(normalizer_meta.boefje_meta.id)

    assert boefje_meta_from_db == normalizer_meta.boefje_meta
    assert normalizer_meta == normalizer_meta_from_db


def test_normalizer_meta_pointing_to_raw_id(meta_repository: SQLMetaDataRepository) -> None:
    with meta_repository:
        boefje_meta = get_boefje_meta()
        meta_repository.save_boefje_meta(boefje_meta)

        raw_id = meta_repository.save_raw(get_raw_data())
        normalizer_meta = get_normalizer_meta(raw_id)

        meta_repository.save_normalizer_meta(normalizer_meta)

    normalizer_meta_from_db = meta_repository.get_normalizer_meta(normalizer_meta.id)
    boefje_meta_from_db = meta_repository.get_boefje_meta_by_id(normalizer_meta.boefje_meta.id)

    assert boefje_meta_from_db == normalizer_meta.boefje_meta
    assert normalizer_meta == normalizer_meta_from_db
