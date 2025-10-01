import time

from celery import Celery

from objects.models import Hostname, Network, ScanLevel
from plugins.models import Plugin
from tasks.models import Schedule, TaskStatus
from tasks.tasks import run_schedule


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
    assert kwargs["network"] == "openkat-test-plugin-network"
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
