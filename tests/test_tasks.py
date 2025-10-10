import operator
import time
from functools import reduce

from celery import Celery
from django.conf import settings
from django.db.models import Q

from files.models import File, GenericContent
from objects.models import Hostname, Network, ScanLevel, bulk_insert
from plugins.models import Plugin
from tasks.models import Schedule, Task, TaskResult, TaskStatus
from tasks.tasks import process_raw_file, run_plugin_task, run_schedule, run_schedule_for_organization


def test_run_schedule(organization, xtdb, celery: Celery, docker, plugin_container):
    logs = [b"test logs"]
    plugin_container.set_logs(logs)

    plugin = Plugin.objects.create(
        name="test", plugin_id="test", oci_image="T", oci_arguments=["{hostname}"], scan_level=2
    )
    plugin.enable_for(organization)
    schedule = Schedule.objects.filter(plugin=plugin).first()

    assert schedule.object_set.name == "All hostnames"
    assert schedule.object_set.object_query == ""
    assert schedule.plugin == plugin
    assert organization in schedule.plugin.enabled_organizations()

    tasks = run_schedule(schedule, force=False, celery=celery)
    assert len(tasks) == 0
    tasks = run_schedule(schedule, force=True, celery=celery)
    assert len(tasks) == 0

    network = Network.objects.create(name="internet")
    host = Hostname.objects.create(name="test.com", network=network)
    sl = ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=host.id)
    time.sleep(0.1)

    tasks = run_schedule(schedule, force=False, celery=celery)
    assert len(tasks) == 0

    sl.scan_level = 2
    sl.save()
    tasks = run_schedule(schedule, force=False, celery=celery)
    assert len(tasks) == 1

    assert tasks[0].data == {"input_data": ["test.com"], "plugin_id": "test"}
    assert tasks[0].type == "plugin"
    assert tasks[0].status == TaskStatus.QUEUED
    assert tasks[0].organization == organization
    assert tasks[0].schedule == schedule

    res = tasks[0].async_result.get()
    assert res == logs[0].decode()
    kwargs = docker.containers.run.mock_calls[0].kwargs

    assert kwargs["image"] == "T"
    assert "test_17" in kwargs["name"]
    assert kwargs["command"] == ["test.com"]
    assert kwargs["stdout"] is False
    assert kwargs["stderr"] is True
    assert kwargs["network"] == settings.DOCKER_NETWORK
    assert kwargs["entrypoint"] == "/bin/runner"
    assert len(kwargs["volumes"]) == 1
    assert kwargs["volumes"][0].endswith("/plugins/plugins/entrypoint/main:/bin/runner")
    assert kwargs["environment"]["PLUGIN_ID"] == plugin.plugin_id
    assert kwargs["environment"]["OPENKAT_API"] == "http://openkat:8000/api/v1"
    assert kwargs["environment"]["UPLOAD_URL"] == f"http://openkat:8000/api/v1/file/?task_id={tasks[0].id}"
    assert "OPENKAT_TOKEN" in kwargs["environment"]
    assert kwargs["detach"] is True

    plugin2 = Plugin.objects.create(
        name="test2", plugin_id="test2", oci_image="T", oci_arguments=["{hostname}"], scan_level=2
    )
    plugin2.enable()
    schedule = Schedule.objects.filter(plugin=plugin2).first()
    assert schedule.object_set.name == "All hostnames"
    assert schedule.object_set.object_query == ""
    assert schedule.plugin == plugin2
    assert schedule.organization is None
    assert organization in schedule.plugin.enabled_organizations()

    tasks = run_schedule(schedule, celery=celery)
    kwargs = docker.containers.run.mock_calls[4].kwargs
    assert kwargs["environment"]["PLUGIN_ID"] == plugin2.plugin_id

    assert len(tasks) == 1


def test_run_schedule_for_none(xtdb, celery: Celery, organization, docker, plugin_container):
    logs = [b"test logs"]
    plugin_container.set_logs(logs)

    plugin = Plugin.objects.create(
        name="test", plugin_id="test", oci_image="T", oci_arguments=["{hostname}"], scan_level=2
    )
    plugin.enable()
    schedule = Schedule.objects.filter(plugin=plugin).first()

    assert schedule.object_set.name == "All hostnames"
    assert schedule.object_set.object_query == ""
    assert schedule.plugin == plugin

    network = Network.objects.create(name="internet")
    host = Hostname.objects.create(name="test.com", network=network)
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=host.id, scan_level=2)
    time.sleep(0.1)

    tasks = run_schedule(schedule, force=False, celery=celery)
    assert len(tasks) == 1


def test_process_raw_file(xtdb, celery: Celery, organization, organization_b, docker, plugin_container):
    logs = [b"test logs"]
    plugin_container.set_logs(logs)

    plugin = Plugin.objects.create(
        name="test", plugin_id="test", consumes=["file:testfile"], oci_image="T", oci_arguments=["{file}"], scan_level=2
    )
    plugin.enable()

    f = File.objects.create(file=GenericContent(b"1234"), type="old")
    f.type = "testfile"  # Avoid the process_raw_file signal
    f.save()
    TaskResult.objects.create(file=f, task=Task.objects.create())

    tasks = process_raw_file(f, celery=celery)
    assert len(tasks) == 1
    assert tasks[0].organization is None

    f = File.objects.create(file=GenericContent(b"4321"), type="old")
    f.type = "testfile"  # Avoid the process_raw_file signal
    f.save()
    TaskResult.objects.create(file=f, task=Task.objects.create(organization=organization_b))

    tasks = process_raw_file(f, celery=celery)
    assert len(tasks) == 1
    assert tasks[0].organization == organization_b

    f = File.objects.create(file=GenericContent(b"4321"), type="old")
    f.type = "testfile"  # Avoid the process_raw_file signal
    f.save()

    tasks = process_raw_file(f, celery=celery)
    assert len(tasks) == 2
    assert {task.organization for task in tasks} == {organization, organization_b}
    assert Task.objects.count() == 6


def test_batch_tasks(xtdb, celery: Celery, organization, organization_b, docker, plugin_container):
    logs = [b"test logs"]
    plugin_container.set_logs(logs)

    plugin = Plugin.objects.create(
        name="test", plugin_id="test", oci_image="T", oci_arguments=["{hostname}"], scan_level=2
    )
    plugin.enable()

    network = Network.objects.create(name="internet")

    hns = []
    sls = []
    for i in range(200):
        host = Hostname(name=f"test{i}.com", network=network)
        hns.append(host)
        sls.append(ScanLevel(organization=organization, object_type="hostname", object_id=host.id, scan_level=2))

    bulk_insert(hns)
    bulk_insert(sls)

    tasks = run_plugin_task(plugin.id, organization.code, input_data=[x.name for x in hns], celery=celery)

    assert len(tasks) == 4
    assert len(tasks[0].data["input_data"]) == 50
    assert len(tasks[1].data["input_data"]) == 50
    assert len(tasks[2].data["input_data"]) == 50
    assert len(tasks[3].data["input_data"]) == 50

    # We check previous tasks only when running for a schedule
    tasks = run_plugin_task(plugin.id, organization.code, input_data=[x.name for x in hns], celery=celery)
    assert len(tasks) == 4


def test_batch_scheduled_tasks(xtdb, celery: Celery, organization, organization_b, mocker):
    mocker.patch("tasks.tasks.run_plugin")
    plugin = Plugin.objects.create(
        name="test", plugin_id="test", oci_image="T", oci_arguments=["{hostname}"], scan_level=2
    )
    plugin.enable()
    schedule = Schedule.objects.first()
    network = Network.objects.create(name="internet")

    hns = []
    sls = []
    for i in range(200):
        host = Hostname(name=f"test{i}.com", network=network)
        hns.append(host)
        sls.append(ScanLevel(organization=organization, object_type="hostname", object_id=host.id, scan_level=2))

    bulk_insert(hns)
    bulk_insert(sls)

    tasks = run_schedule_for_organization(schedule, organization, force=False, celery=celery)

    assert len(tasks) == 4
    assert len(tasks[0].data["input_data"]) == 50
    assert len(tasks[1].data["input_data"]) == 50
    assert len(tasks[2].data["input_data"]) == 50
    assert len(tasks[3].data["input_data"]) == 50

    tasks = run_schedule_for_organization(schedule, organization, force=False, celery=celery)
    assert len(tasks) == 0


def test_find_intersecting_input_data(organization):
    data = ["1.com"]
    Task.objects.create(organization=organization, type="plugin", data={"plugin_id": "test", "input_data": data})

    data = ["3.com", "4.com", "5.com"]
    Task.objects.create(organization=organization, type="plugin", data={"plugin_id": "test", "input_data": data})

    data = ["4.com", "5.com"]
    Task.objects.create(organization=organization, type="plugin", data={"plugin_id": "test", "input_data": data})

    # old style vs new style
    target = ["0.com"]
    assert Task.objects.filter(reduce(operator.or_, [Q(data__input_data__icontains=x) for x in target])).count() == 0
    assert Task.objects.filter(data__input_data__has_any_keys=target).count() == 0

    target = ["1.com"]
    assert Task.objects.filter(reduce(operator.or_, [Q(data__input_data__icontains=x) for x in target])).count() == 1
    assert Task.objects.filter(data__input_data__has_any_keys=target).count() == 1

    target = ["4.com"]
    assert Task.objects.filter(reduce(operator.or_, [Q(data__input_data__icontains=x) for x in target])).count() == 2
    assert Task.objects.filter(data__input_data__has_any_keys=target).count() == 2

    target = ["4.com", "5.com"]
    assert Task.objects.filter(reduce(operator.or_, [Q(data__input_data__icontains=x) for x in target])).count() == 2
    assert Task.objects.filter(data__input_data__has_any_keys=target).count() == 2

    target = ["4.com", "5.com", "6.com"]
    assert Task.objects.filter(reduce(operator.or_, [Q(data__input_data__icontains=x) for x in target])).count() == 2
    assert Task.objects.filter(data__input_data__has_any_keys=target).count() == 2
