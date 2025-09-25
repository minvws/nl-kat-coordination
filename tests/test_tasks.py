from celery import Celery

from objects.models import Hostname, Network
from plugins.models import Plugin
from tasks.models import Schedule, TaskStatus
from tasks.tasks import run_schedule


def test_plugin_list(organization, superuser_member, xtdb, celery: Celery, docker, container):
    logs = [b"test logs"]
    container.set_logs(logs)

    plugin = Plugin.objects.create(name="test", plugin_id="test", oci_image="T", oci_arguments=["{hostname}"])
    plugin.enable_for(organization)

    schedule = Schedule.objects.first()

    assert schedule

    tasks = run_schedule(schedule, celery=celery)
    assert len(tasks) == 0

    network = Network.objects.create(name="internet")
    Hostname.objects.create(name="test.com", network=network)

    tasks = run_schedule(schedule, celery=celery)
    assert len(tasks) == 1

    assert tasks[0].data == {"input_data": ["test.com"], "plugin_id": "test"}
    assert tasks[0].type == "plugin"
    assert tasks[0].status == TaskStatus.QUEUED
    assert tasks[0].organization == organization
    assert tasks[0].schedule == schedule

    res = tasks[0].async_result.get()
    assert res == logs[0].decode()
