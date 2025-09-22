import operator
import uuid
from datetime import UTC, datetime
from functools import reduce
from typing import Any

import structlog
from django.conf import settings
from django.db.models import Q
from djangoql.queryset import apply_search

from files.models import File
from openkat.models import Organization
from plugins.models import Plugin
from plugins.runner import PluginRunner
from tasks.celery import app
from tasks.models import Schedule, Task, TaskStatus

logger = structlog.get_logger(__name__)


@app.task(queue=settings.QUEUE_NAME_SCAN_PROFILES)
def schedule_scan_profile_recalculations():
    orgs = Organization.objects.all()
    logger.info("Scheduling scan profile recalculation for %s organizations", len(orgs))

    for org in orgs:
        app.send_task(
            "tasks.tasks.recalculate_scan_profiles",
            (org.code,),
            queue=settings.QUEUE_NAME_SCAN_PROFILES,
            task_id=str(uuid.uuid4()),
        )


@app.task(queue=settings.QUEUE_NAME_SCAN_PROFILES)
def recalculate_scan_profiles(org: str, *args: Any, **kwargs: Any) -> None:
    # TODO: fix
    return


@app.task(queue=settings.QUEUE_NAME_SCHEDULE)
def reschedule() -> None:
    logger.info("Scheduling plugins")

    for schedule in Schedule.objects.filter(enabled=True):
        run_schedule(schedule, force=False)

    logger.info("Finished scheduling plugins")


def run_schedule(schedule: Schedule, force: bool = True) -> None:
    if not schedule.plugin:
        return

    orgs = schedule.plugin.enabled_organizations() if not schedule.organization else [schedule.organization]

    for org in orgs:
        run_schedule_for_org(schedule, org, force)


def run_schedule_for_org(schedule: Schedule, organization: Organization, force: bool = True) -> None:
    now = datetime.now(UTC)

    if not schedule.object_set:
        if force:
            run_plugin_task(schedule.plugin.plugin_id, organization.code, None, schedule.id)
            return

        last_run = Task.objects.filter(new_schedule=schedule, data__input_data=None).order_by("-created_at").first()
        if last_run and not schedule.recurrences.between(last_run.created_at, now):
            logger.debug("Plugin '%s' has already run recently", schedule.plugin.plugin_id)
            return

        run_plugin_task(schedule.plugin.plugin_id, organization.code, None, schedule.id)
        return

    input_data: set[str] = set()

    if schedule.object_set.object_query is not None and schedule.object_set.dynamic is True:
        model_qs = schedule.object_set.object_type.model_class().objects.all()

        if schedule.object_set.object_query:
            model_qs = apply_search(model_qs, schedule.object_set.object_query)

        # TODO: check scan profile
        input_data = input_data.union([str(model) for model in model_qs])

    if not input_data:
        return

    # TODO: fix
    # values = schedule.object_set.traverse_objects().values_list("value", flat=True)

    # if not values and not input_data:
    #     return
    # for profile in scan_profiles:
    #     if profile.level.value < schedule.plugin.scan_level or str(profile.reference) not in values:
    #         continue
    #
    #     if profile.reference.class_type == Hostname:
    #         input_data.add(profile.reference.tokenized.name)
    #         continue
    #
    #     if profile.reference.class_type in [IPAddressV4, IPAddressV6]:
    #         input_data.add(str(profile.reference.tokenized.address))
    #         continue
    #
    #     input_data.add(str(profile.reference))

    if force:
        run_plugin_task(schedule.plugin.plugin_id, organization.code, input_data, schedule.id)
        return

    # Filter on the schedule and created after the previous occurrence
    last_runs = Task.objects.filter(new_schedule=schedule, created_at__gt=schedule.recurrences.before(now))

    if input_data:
        # Join the input data targets into a large or-query, checking for task with any of the targets as input
        filters = reduce(
            operator.or_, [Q(data__input_data__icontains=target) | Q(data__input_data=target) for target in input_data]
        )
        last_runs = last_runs.filter(filters)

    skip = set()

    for target in last_runs.values_list("data__input_data", flat=True):
        if isinstance(target, list):
            skip |= set(target)
        else:
            skip.add(target)

    # filter out these targets
    input_data = set(input_data) - skip

    if not input_data:
        return

    run_plugin_task(schedule.plugin.plugin_id, organization.code, input_data, schedule.id)


def rerun_task(task: Task) -> list[Task]:
    plugin = Plugin.objects.get(plugin_id=task.data["plugin_id"])

    return run_plugin_task(
        plugin.plugin_id, task.organization.code if task.organization else None, task.data["input_data"], None
    )


def run_plugin_task(
    plugin_id: str,
    organization_code: str | None = None,
    input_data: str | list[str] | set[str] | None = None,
    schedule_id: int | None = None,
    batch: bool = True,
) -> list[Task]:
    if isinstance(input_data, set):
        input_data = list(input_data)

    if batch and isinstance(input_data, list) and settings.BATCH_SIZE > 0 and len(input_data) > settings.BATCH_SIZE:
        tasks = []
        idx = 0

        for idx_2 in range(settings.BATCH_SIZE, len(input_data) + settings.BATCH_SIZE, settings.BATCH_SIZE):
            tasks.append(run_plugin_task(plugin_id, organization_code, input_data[idx:idx_2], batch=False)[0])
            idx = idx_2

        return tasks

    task_id = uuid.uuid4()
    task = Task.objects.create(
        id=task_id,
        type="plugin",
        new_schedule_id=schedule_id,
        organization=Organization.objects.get(code=organization_code) if organization_code else None,
        status=TaskStatus.QUEUED,
        data={"plugin_id": plugin_id, "input_data": input_data},  # TODO
    )

    app.send_task("tasks.tasks.run_plugin", (plugin_id, organization_code, input_data), task_id=str(task_id))

    return [task]


@app.task(bind=True)
def run_plugin(
    self, plugin_id: str, organization_code: str | None = None, input_data: str | list[str] | None = None
) -> None:
    logger.debug(
        "Starting plugin task",
        task_id=self.request.id,
        organization=organization_code,
        plugin_id=plugin_id,
        input_data=input_data,
    )
    organization: Organization | None = None
    task = Task.objects.get(id=self.request.id)

    if organization_code:
        organization = Organization.objects.get(code=organization_code)

    plugin = Plugin.objects.filter(plugin_id=plugin_id).first()

    if not plugin or not plugin.enabled_for(organization):
        task.status = TaskStatus.FAILED
        task.save()
        raise RuntimeError(f"Plugin {plugin_id} is not enabled for {organization_code}")

        Task.objects.filter(id=self.request.id).update(status=TaskStatus.RUNNING)

    task.status = TaskStatus.RUNNING
    task.save()

    try:
        PluginRunner().run(plugin_id, input_data, task_id=task.id)
        task.status = TaskStatus.COMPLETED
        task.ended_at = datetime.now(UTC)
        task.save()
    except:
        task.refresh_from_db(fields=["status"])

        if task.status != TaskStatus.CANCELLED:
            task.status = TaskStatus.FAILED

        task.ended_at = datetime.now(UTC)
        task.save()
        raise

    logger.info("Handled plugin", organization=organization, plugin_id=plugin_id, input_data=input_data)


def process_raw_file(file: File, handle_error: bool = False):
    if file.type == "error" and not handle_error:
        logger.info("Raw file %s contains an exception trace and handle_error is set to False. Skipping.", file.id)
        return

    for plugin in Plugin.objects.filter(consumes__contains=[f"file:{file.type}"]):
        for organization in plugin.enabled_organizations():
            run_plugin_task(plugin.plugin_id, organization.code, str(file.id))
