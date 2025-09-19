import pytest

from tasks.models import ObjectSet

# TODO: fix
pytestmark = pytest.mark.skip


def test_traverse():
    first_objs = [Object.objects.create(type=f"first test{i}", value=f"first_test{i}.com") for i in range(10)]

    object_set = ObjectSet.objects.create()

    for obj in first_objs:
        object_set.all_objects.add(obj)

    object_set.save()

    # all_objects equals the complete object dataset
    assert Object.objects.all().difference(object_set.all_objects.all()).count() == 0
    assert Object.objects.all().difference(object_set.traverse_objects().all()).count() == 0

    second_objs = [Object.objects.create(type=f"second test{i}", value=f"second_test{i}.com") for i in range(10)]

    # all_objects still equals the complete first object dataset
    assert Object.objects.filter(type__contains="first").difference(object_set.all_objects.all()).count() == 0
    assert Object.objects.filter(type__contains="first").difference(object_set.traverse_objects().all()).count() == 0

    # But not the total dataset
    assert Object.objects.all().difference(object_set.all_objects.all()).count() == 10
    assert Object.objects.all().difference(object_set.traverse_objects().all()).count() == 10

    second_object_set = ObjectSet.objects.create()

    for obj in second_objs:
        second_object_set.all_objects.add(obj)

    second_object_set.save()

    assert Object.objects.all().difference(object_set.all_objects.all()).count() == 10
    assert Object.objects.all().difference(object_set.traverse_objects().all()).count() == 10
    assert Object.objects.all().difference(second_object_set.all_objects.all()).count() == 10
    assert Object.objects.all().difference(second_object_set.traverse_objects().all()).count() == 10
    assert Object.objects.filter(type__contains="second").difference(object_set.all_objects.all()).count() == 10
    assert Object.objects.filter(type__contains="second").difference(object_set.traverse_objects().all()).count() == 10
    assert Object.objects.filter(type__contains="second").difference(second_object_set.all_objects.all()).count() == 0
    assert (
        Object.objects.filter(type__contains="second").difference(second_object_set.traverse_objects().all()).count()
        == 0
    )

    third_object_set = ObjectSet.objects.create()

    third_object_set.subsets.add(object_set)
    third_object_set.subsets.add(second_object_set)
    third_object_set.save()

    # The third object set combines the first two object sets and hence contains the whole dataset (composite-pattern)
    assert Object.objects.all().difference(third_object_set.all_objects.all()).count() == 20
    assert Object.objects.all().difference(third_object_set.traverse_objects().all()).count() == 0

    assert second_object_set.traverse_objects(max_depth=1)

    with pytest.raises(RecursionError):
        third_object_set.traverse_objects(max_depth=1)


def test_query_values():
    first_objs = [Object.objects.create(type=f"first test{i}", value=f"first_test{i}.com") for i in range(10)]

    object_set = ObjectSet.objects.create()

    for obj in first_objs:
        object_set.all_objects.add(obj)

    object_set.save()

    assert list(object_set.traverse_objects().values_list("value", flat=True)) == [
        "first_test0.com",
        "first_test1.com",
        "first_test2.com",
        "first_test3.com",
        "first_test4.com",
        "first_test5.com",
        "first_test6.com",
        "first_test7.com",
        "first_test8.com",
        "first_test9.com",
    ]
