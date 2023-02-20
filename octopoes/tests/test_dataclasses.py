def test_human_readable(animal):
    assert animal.human_readable == "Hello: Whiskers"


def test_human_readable_nested(zookeeper):
    assert zookeeper.human_readable == "Leslie pets Whiskers"


def test_object_dependencies(animal, zookeeper):
    assert list(zookeeper.dependencies()) == [animal, zookeeper]


def test_object_dependencies_not_including_self(animal, zookeeper):
    assert list(zookeeper.dependencies(include_self=False)) == [animal]
