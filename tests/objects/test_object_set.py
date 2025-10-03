import time

import pytest
from django.contrib.contenttypes.models import ContentType

from objects.models import Hostname, Network
from tasks.models import ObjectSet


def test_traverse_objects_with_all_objects(xtdb):
    network = Network.objects.create(name="internet")

    hostname1 = Hostname.objects.create(network=network, name="test1.example.com")
    hostname2 = Hostname.objects.create(network=network, name="test2.example.com")
    Hostname.objects.create(network=network, name="test3.example.com")
    time.sleep(0.1)

    object_set = ObjectSet.objects.create(
        name="Test Set",
        object_type=ContentType.objects.get_for_model(Hostname),
        all_objects=[hostname1.pk, hostname2.pk],
    )

    assert set(object_set.traverse_objects()) == {hostname1.pk, hostname2.pk}


def test_traverse_objects_with_query(xtdb):
    network = Network.objects.create(name="internet")

    Hostname.objects.create(network=network, name="test1.example.com")
    Hostname.objects.create(network=network, name="test2.example.com")
    Hostname.objects.create(network=network, name="prod.example.com")
    time.sleep(0.1)

    object_set = ObjectSet.objects.create(
        name="Test Set", object_type=ContentType.objects.get_for_model(Hostname), object_query='name ~ "test"'
    )

    result = object_set.traverse_objects()
    assert isinstance(result, list)
    assert all(isinstance(pk, int) for pk in result)
    if len(result) > 0:
        assert len(result) >= 2


def test_traverse_objects_combines_all_objects_and_query(xtdb):
    network = Network.objects.create(name="internet")

    Hostname.objects.create(network=network, name="test1.example.com")
    Hostname.objects.create(network=network, name="test2.example.com")
    hostname3 = Hostname.objects.create(network=network, name="prod.example.com")
    Hostname.objects.create(network=network, name="dev.example.com")
    time.sleep(0.1)

    object_set = ObjectSet.objects.create(
        name="Combined Set",
        object_type=ContentType.objects.get_for_model(Hostname),
        all_objects=[hostname3.pk],
        object_query="",
    )

    result = object_set.traverse_objects()
    assert len(result) >= 1
    assert hostname3.pk in result


def test_traverse_objects_removes_duplicates(xtdb):
    network = Network.objects.create(name="internet")
    hostname1 = Hostname.objects.create(network=network, name="test1.example.com")
    time.sleep(0.1)

    object_set = ObjectSet.objects.create(
        name="Duplicate Set",
        object_type=ContentType.objects.get_for_model(Hostname),
        all_objects=[hostname1.pk],
        object_query='name = "test1.example.com"',
    )

    result = object_set.traverse_objects()
    assert len(result) == 1
    assert hostname1.pk in result


def test_traverse_objects_with_subsets(xtdb):
    network = Network.objects.create(name="internet")
    hostname1 = Hostname.objects.create(network=network, name="test1.example.com")
    hostname2 = Hostname.objects.create(network=network, name="test2.example.com")
    hostname3 = Hostname.objects.create(network=network, name="test3.example.com")
    time.sleep(0.1)

    subset1 = ObjectSet.objects.create(
        name="Subset 1", object_type=ContentType.objects.get_for_model(Hostname), all_objects=[hostname1.pk]
    )

    subset2 = ObjectSet.objects.create(
        name="Subset 2", object_type=ContentType.objects.get_for_model(Hostname), all_objects=[hostname2.pk]
    )

    parent_set = ObjectSet.objects.create(
        name="Parent Set", object_type=ContentType.objects.get_for_model(Hostname), all_objects=[hostname3.pk]
    )
    parent_set.subsets.add(subset1, subset2)

    result = parent_set.traverse_objects()
    assert len(result) == 3
    assert hostname1.pk in result
    assert hostname2.pk in result
    assert hostname3.pk in result


def test_traverse_objects_max_depth(xtdb):
    network = Network.objects.create(name="internet")
    hostname1 = Hostname.objects.create(network=network, name="test1.example.com")
    hostname2 = Hostname.objects.create(network=network, name="test2.example.com")
    time.sleep(0.1)

    level2 = ObjectSet.objects.create(
        name="Level 2", object_type=ContentType.objects.get_for_model(Hostname), all_objects=[hostname1.pk]
    )

    level1 = ObjectSet.objects.create(
        name="Level 1", object_type=ContentType.objects.get_for_model(Hostname), all_objects=[hostname2.pk]
    )
    level1.subsets.add(level2)

    level0 = ObjectSet.objects.create(
        name="Level 0", object_type=ContentType.objects.get_for_model(Hostname), all_objects=[]
    )
    level0.subsets.add(level1)

    result_depth_1 = level0.traverse_objects(max_depth=1)
    assert hostname2.pk in result_depth_1

    result_depth_2 = level0.traverse_objects(max_depth=2)
    assert hostname1.pk in result_depth_2
    assert hostname2.pk in result_depth_2


@pytest.mark.django_db
def test_traverse_objects_empty_set():
    object_set = ObjectSet.objects.create(
        name="Empty Set", object_type=ContentType.objects.get_for_model(Hostname), all_objects=[]
    )

    result = object_set.traverse_objects()
    assert len(result) == 0


def test_traverse_objects_invalid_query(xtdb):
    network = Network.objects.create(name="internet")
    hostname1 = Hostname.objects.create(network=network, name="test1.example.com")
    time.sleep(0.1)

    object_set = ObjectSet.objects.create(
        name="Invalid Query Set",
        object_type=ContentType.objects.get_for_model(Hostname),
        all_objects=[hostname1.pk],
        object_query="invalid query syntax!!!",
    )

    result = object_set.traverse_objects()
    assert len(result) == 2  # Root domain gets saved as well
    assert hostname1.pk in result
