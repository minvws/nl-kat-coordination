from octopoes.repositories.object_repository import ObjectRepository


def test_prefix_fields():
    obj = {
        "object_type": "test_object_type",
        "primary_key": "test_pk",
        "human_readable": "test_hr",
        "test_prop": "test_prop",
    }
    expected = {
        "object_type": "test_object_type",
        "primary_key": "test_pk",
        "human_readable": "test_hr",
        "test_object_type/test_prop": "test_prop",
        "xt/id": "test_pk",
    }
    assert ObjectRepository.prefix_fields(obj) == expected


def test_serialize_obj(animal):
    expected = {
        "object_type": "Animal",
        "primary_key": "722dfb0a405fe4838ab9751a815ebce6",
        "human_readable": "Hello: Whiskers",
        "Animal/name": "Whiskers",
        "Animal/color": "red",
        "xt/id": "722dfb0a405fe4838ab9751a815ebce6",
    }
    assert ObjectRepository.serialize_obj(animal) == expected


def test_nested_serialize_obj(zookeeper):
    expected = {
        "object_type": "ZooKeeper",
        "primary_key": "936bd20b157951d68e3276ab44e89c20",
        "human_readable": "Leslie pets Whiskers",
        "ZooKeeper/name": "Leslie",
        "ZooKeeper/pet": "722dfb0a405fe4838ab9751a815ebce6",
        "xt/id": "936bd20b157951d68e3276ab44e89c20",
    }
    assert ObjectRepository.serialize_obj(zookeeper) == expected
