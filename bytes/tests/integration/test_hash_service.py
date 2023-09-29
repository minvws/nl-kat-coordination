import pytest

from bytes.database.sql_meta_repository import SQLMetaDataRepository
from bytes.repositories.meta_repository import RawDataFilter
from bytes.timestamping.pastebin import PastebinHashRepository
from tests.loading import get_boefje_meta, get_raw_data


@pytest.mark.skipif("not has_pastebin_key()")
def test_save_raw_data_pastebin(
    meta_repository: SQLMetaDataRepository, pastebin_hash_repository: PastebinHashRepository
) -> None:
    meta = get_boefje_meta()

    with meta_repository:
        meta_repository.save_boefje_meta(meta)

    with meta_repository:
        meta_repository.save_raw(raw=get_raw_data())

    query_filter = RawDataFilter(boefje_meta_id=meta.id)
    raws = meta_repository.get_raw(query_filter)

    assert (
        raws[0].secure_hash == "sha512:bc4d1f0a71ba9bf2ab2b7520322f8e969c48d5ae99e84b4a60b850f61ce"
        "5b1e95e13f3ef6c43680fb03960f98799a92770e30591253784cc3213b194a73ea21d"
    )
    assert raws[0].hash_retrieval_link is not None
    assert "https://pastebin.com/" in raws[0].hash_retrieval_link

    retrieved_hash = pastebin_hash_repository.retrieve(raws[0].hash_retrieval_link)

    assert (
        retrieved_hash == "sha512:bc4d1f0a71ba9bf2ab2b7520322f8e969c48d5ae99e84b4a60b850f61ce"
        "5b1e95e13f3ef6c43680fb03960f98799a92770e30591253784cc3213b194a73ea21d"
    )
