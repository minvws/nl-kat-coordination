import pytest
from rest_framework import status

from objects.models import Network, TaskObjects
from tasks.models import Task, TaskStatus


@pytest.fixture
def task_objects_data(xtdb):
    TaskObjects.objects.create(
        task_id=1, plugin_id="dns", input_objects=["example.com"], output_objects=["192.168.1.1", "192.168.1.2"]
    )
    TaskObjects.objects.create(
        task_id=2, plugin_id="nmap", input_objects=["192.168.1.0/24"], output_objects=["192.168.1.10", "192.168.1.20"]
    )
    TaskObjects.objects.create(task_id=3, plugin_id="dns", input_objects=["test.com"], output_objects=["10.0.0.1"])


def test_create_task_objects(xtdb, log_output):
    task_obj = TaskObjects.objects.create(
        task_id=123,
        type="plugin",
        plugin_id="test_plugin",
        input_objects=["hostname1", "hostname2"],
        output_objects=["ipaddress1"],
    )

    assert task_obj.task_id == 123
    assert task_obj.type == "plugin"
    assert task_obj.plugin_id == "test_plugin"
    assert task_obj.input_objects == ["hostname1", "hostname2"]
    assert task_obj.output_objects == ["ipaddress1"]


def test_task_objects_default_values(xtdb):
    task_obj = TaskObjects.objects.create(task_id=456, plugin_id="test_plugin")

    assert task_obj.type == "plugin"
    assert task_obj.input_objects == []
    assert task_obj.output_objects == []


def test_task_objects_json_fields_accept_lists(xtdb):
    task_obj = TaskObjects.objects.create(
        task_id=789,
        plugin_id="test_plugin",
        input_objects=["obj1", "obj2", "obj3"],
        output_objects=["result1", "result2"],
    )

    task_obj.refresh_from_db()
    assert isinstance(task_obj.input_objects, list)
    assert isinstance(task_obj.output_objects, list)
    assert len(task_obj.input_objects) == 3
    assert len(task_obj.output_objects) == 2


def test_task_objects_extend_output_objects(xtdb):
    task_obj = TaskObjects.objects.create(task_id=111, plugin_id="test_plugin", output_objects=["obj1"])

    task_obj.output_objects.extend(["obj2", "obj3"])
    task_obj.save()

    task_obj.refresh_from_db()
    assert task_obj.output_objects == ["obj1", "obj2", "obj3"]


def test_task_objects_get_or_create_pattern(xtdb):
    task_obj, created = TaskObjects.objects.get_or_create(
        task_id=222, defaults=dict(plugin_id="test_plugin", input_objects=["input1"])
    )

    assert created is True
    assert task_obj.task_id == 222
    assert task_obj.plugin_id == "test_plugin"

    # Try to get the same object
    task_obj2, created2 = TaskObjects.objects.get_or_create(
        task_id=222, defaults=dict(plugin_id="other_plugin", input_objects=["input2"])
    )

    assert created2 is False
    assert task_obj2.pk == task_obj.pk
    assert task_obj2.plugin_id == "test_plugin"  # Original value preserved


def test_create_hostname_with_task_id(drf_client, xtdb):
    task = Task.objects.create(type="plugin", data={"plugin_id": "dns", "input_data": ["test.example.com"]})
    network = Network.objects.create(name="test-network")
    url = f"/api/v1/objects/hostname/?task_id={task.pk}"
    data = {"network": network.pk, "name": "example.com"}

    response = drf_client.post(url, json=data)

    assert response.status_code == status.HTTP_201_CREATED

    task_obj = TaskObjects.objects.get(task_id=task.pk)
    assert task_obj.plugin_id == "dns"
    assert task_obj.input_objects == ["test.example.com"]
    assert "example.com" in task_obj.output_objects


def test_create_ipaddress_with_task_id(drf_client, xtdb):
    task = Task.objects.create(type="plugin", data={"plugin_id": "dns", "input_data": ["test.example.com"]})
    network = Network.objects.create(name="test-network")
    url = f"/api/v1/objects/ipaddress/?task_id={task.pk}"
    data = {"network": network.pk, "address": "192.168.1.1"}

    response = drf_client.post(url, json=data)

    assert response.status_code == status.HTTP_201_CREATED

    task_obj = TaskObjects.objects.get(task_id=task.pk)
    assert task_obj.plugin_id == "dns"
    assert "192.168.1.1" in task_obj.output_objects


def test_create_multiple_objects_same_task(drf_client, xtdb):
    task = Task.objects.create(type="plugin", data={"plugin_id": "dns", "input_data": ["test.example.com"]})
    network = Network.objects.create(name="test-network")
    url = f"/api/v1/objects/hostname/?task_id={task.pk}"

    data1 = {"network": network.pk, "name": "first.example.com"}
    response1 = drf_client.post(url, json=data1)
    assert response1.status_code == status.HTTP_201_CREATED

    data2 = {"network": network.pk, "name": "second.example.com"}
    response2 = drf_client.post(url, json=data2)
    assert response2.status_code == status.HTTP_201_CREATED

    task_obj = TaskObjects.objects.get(task_id=task.pk)
    assert "first.example.com" in task_obj.output_objects
    assert "second.example.com" in task_obj.output_objects
    assert len(task_obj.output_objects) == 2


def test_create_without_task_id_no_task_objects(drf_client, xtdb):
    network = Network.objects.create(name="test-network")
    url = "/api/v1/objects/hostname/"
    data = {"network": network.pk, "name": "notask.example.com"}

    response = drf_client.post(url, json=data)

    assert response.status_code == status.HTTP_201_CREATED
    assert TaskObjects.objects.count() == 0


def test_task_objects_tracks_different_object_types(drf_client, xtdb):
    task = Task.objects.create(type="plugin", data={"plugin_id": "dns", "input_data": ["test.example.com"]})
    network = Network.objects.create(name="test-network")

    hostname_url = f"/api/v1/objects/hostname/?task_id={task.pk}"
    hostname_data = {"network": network.pk, "name": "example.com"}
    drf_client.post(hostname_url, json=hostname_data)

    ip_url = f"/api/v1/objects/ipaddress/?task_id={task.pk}"
    ip_data = {"network": network.pk, "address": "192.168.1.1"}
    drf_client.post(ip_url, json=ip_data)

    task_obj = TaskObjects.objects.get(task_id=task.pk)
    assert "example.com" in task_obj.output_objects
    assert "192.168.1.1" in task_obj.output_objects


def test_task_objects_with_nonexistent_task_raises_error(drf_client, xtdb):
    network = Network.objects.create(name="test-network")
    url = "/api/v1/objects/hostname/?task_id=99999"
    data = {"network": network.pk, "name": "error.example.com"}

    with pytest.raises(Task.DoesNotExist):
        drf_client.post(url, json=data)


def test_task_objects_preserves_input_objects(drf_client, xtdb):
    network = Network.objects.create(name="test-network")
    task = Task.objects.create(
        type="plugin",
        status=TaskStatus.RUNNING,
        data={"plugin_id": "nmap", "input_data": ["192.168.1.1", "192.168.1.2", "192.168.1.3"]},
    )

    url = f"/api/v1/objects/ipaddress/?task_id={task.pk}"
    data = {"network": network.pk, "address": "10.0.0.1"}

    response = drf_client.post(url, json=data)
    assert response.status_code == status.HTTP_201_CREATED

    task_obj = TaskObjects.objects.get(task_id=task.pk)
    assert task_obj.input_objects == ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
    assert "10.0.0.1" in task_obj.output_objects


def test_filter_by_task_id(task_objects_data):
    task_obj = TaskObjects.objects.get(task_id=1)
    assert task_obj.plugin_id == "dns"
    assert len(task_obj.output_objects) == 2


def test_filter_by_plugin_id(task_objects_data):
    dns_tasks = TaskObjects.objects.filter(plugin_id="dns")
    assert dns_tasks.count() == 2

    nmap_tasks = TaskObjects.objects.filter(plugin_id="nmap")
    assert nmap_tasks.count() == 1


def test_query_output_objects(task_objects_data):
    tasks_with_ip = TaskObjects.objects.filter(output_objects__contains=["192.168.1.1"])
    assert tasks_with_ip.count() == 1
    assert tasks_with_ip.first().task_id == 1


def test_count_total_outputs(task_objects_data):
    all_tasks = TaskObjects.objects.all()
    total_outputs = sum(len(task.output_objects) for task in all_tasks)
    assert total_outputs == 5  # 2 + 2 + 1
