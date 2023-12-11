from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.origin import Origin, OriginType
from octopoes.xtdb.client import OperationType


def raise_(exception):
    raise exception


def test_save_new_origin(origin_repository, valid_time, mocker):
    origin = Origin(origin_type=OriginType.INFERENCE, method="method", source="source")
    mocker.patch.object(origin_repository, "get", lambda origin_id, valid_time: raise_(ObjectNotFoundException("test")))
    origin_repository.save(origin, valid_time)

    assert len(origin_repository.session._operations) == 1
    assert origin_repository.session._operations[0][0] == OperationType.PUT
    assert len(origin_repository.session.post_commit_callbacks) == 1


def test_save_existing_origin(origin_repository, valid_time, mocker):
    origin = Origin(origin_type=OriginType.INFERENCE, method="method", source="source")
    mocker.patch.object(origin_repository, "get", lambda origin_id, valid_time: origin)
    origin_repository.save(origin, valid_time)

    assert origin_repository.session._operations == []
    assert len(origin_repository.session.post_commit_callbacks) == 0


def test_save_new_task_id_origin(origin_repository, valid_time, mocker):
    old_origin = Origin(
        origin_type=OriginType.OBSERVATION,
        method="method",
        source="source",
        task_id="52f4cf94-fd28-4650-a65a-9bf7c2b50c41",
    )
    new_origin = Origin(
        origin_type=OriginType.OBSERVATION,
        method="method",
        source="source",
        task_id="08dd2ef8-353a-42b0-8d54-07ef1362b843",
    )
    mocker.patch.object(origin_repository, "get", lambda origin_id, valid_time: old_origin)
    origin_repository.save(new_origin, valid_time)

    operations = origin_repository.session._operations
    assert len(operations) == 2
    assert operations[0][0] == OperationType.DELETE
    assert operations[0][1] == old_origin.id
    assert operations[1][0] == OperationType.PUT
    assert len(origin_repository.session.post_commit_callbacks) == 0
