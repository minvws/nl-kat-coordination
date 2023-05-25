from bytes.config import has_rfc3161_provider  # noqa: F401
from bytes.database.sql_meta_repository import SQLMetaDataRepository
from bytes.repositories.hash_repository import HashRepository
from bytes.repositories.meta_repository import RawDataFilter
from tests.loading import get_boefje_meta, get_raw_data


def test_rfc3161_external_api(meta_repository: SQLMetaDataRepository, mock_hash_repository: HashRepository) -> None:
    meta = get_boefje_meta()

    with meta_repository:
        meta_repository.save_boefje_meta(meta)

    with meta_repository:
        meta_repository.save_raw(raw=get_raw_data())

    query_filter = RawDataFilter(boefje_meta_id=meta.id)
    raws = meta_repository.get_raw(query_filter)

    assert (
        raws[0].secure_hash == "sha512:cab5427ae5ac87ff6d1ed0d1f05542795a0419a6e6e1fd67ba0754a114a"
        "d136a47027ed3805e9e573352f451cb27850d7006a5edd6d86b35ec855b8af37a924a"
    )
    assert raws[0].hash_retrieval_link is not None

    assert mock_hash_repository.verify(raws[0].hash_retrieval_link, raws[0].secure_hash)
