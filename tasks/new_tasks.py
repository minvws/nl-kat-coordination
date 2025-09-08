import operator
import uuid
from datetime import datetime, timezone
from functools import reduce

import structlog
from django.conf import settings
from django.db.models import Q

from files.models import File
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.exception import TypeNotFound
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from octopoes.xtdb.query import Aliased, Query
from openkat.models import Organization
from plugins.models import Plugin
from plugins.runner import PluginRunner
from tasks.celery import app
from tasks.models import NewSchedule, Task, TaskStatus

logger = structlog.get_logger(__name__)


@app.task(queue=settings.QUEUE_NAME_SCHEDULE)
def reschedule() -> None:
    logger.info("Scheduling plugins")

    for schedule in NewSchedule.objects.filter(enabled=True):
        run_schedule(schedule, force=False)

    logger.info("Finished scheduling plugins")


def run_schedule(schedule: NewSchedule, force: bool = True):
    if not schedule.plugin:
        pass

    now = datetime.now(timezone.utc)
    orgs = schedule.plugin.enabled_organizations() if not schedule.organization else [schedule.organization]

    for org in orgs:
        connector: OctopoesAPIConnector = settings.OCTOPOES_FACTORY(org.code)

        if not schedule.object_set:
            last_run = Task.objects.filter(new_schedule=schedule, data__input_data=None).order_by("-created_at").first()
            if last_run and not schedule.recurrences.between(last_run.created_at, now):
                logger.debug("Plugin '%s' has already run recently", schedule.plugin.plugin_id)
                continue

            run_plugin_task(schedule.plugin.plugin_id, org.code, None, schedule.id)
            continue

        # TODO: will be replaced with direct(er) queries in XTDB 2.0

        if schedule.object_set.object_query:
            try:
                query = Query.from_path(schedule.object_set.object_query)
            except (ValueError, TypeNotFound):
                raise ValueError(f"Invalid query: {schedule.object_set.object_query}")

            pk = Aliased(query.result_type, field="primary_key")

            objects = connector.octopoes.ooi_repository.query(
                query.find(pk).where(query.result_type, primary_key=pk), now
            )
            by_pk = {item[-1]: item[0] for item in objects}
            scan_profiles = connector.octopoes.scan_profile_repository.get_bulk([x for x in by_pk], now)

            input_data = list(
                sorted(
                    [
                        by_pk[str(profile.reference)]
                        for profile in scan_profiles
                        if profile.level.value >= schedule.plugin.scan_level
                    ]
                )
            )

            if not force:
                # Filter on the schedule and created after the previous occurrence
                last_runs = Task.objects.filter(new_schedule=schedule, created_at__gt=schedule.recurrences.before(now))

                if input_data:
                # Join the input data targets into a large or-query, checking for task with any of the targets as input
                    filters = reduce(
                        operator.or_,
                        [Q(data__input_data__icontains=target) | Q(data__input_data=target) for target in input_data],
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
                    continue

            run_plugin_task(schedule.plugin.plugin_id, org.code, input_data, schedule.id)
        else:
            values = schedule.object_set.traverse_objects().values_list("value", flat=True)
            scan_profiles = connector.octopoes.scan_profile_repository.get_bulk(list(values), now)
            input_data = set()

            for profile in scan_profiles:
                if profile.level.value < schedule.plugin.scan_level or str(profile.reference) not in values:
                    continue

                if profile.reference.class_type == Hostname:
                    input_data.add(profile.reference.tokenized.name)
                    continue

                if profile.reference.class_type in [IPAddressV4, IPAddressV6]:
                    input_data.add(str(profile.reference.tokenized.address))
                    continue

                input_data.add(str(profile.reference))

            # TODO: deduplicate
            if not force:
                # Filter on the schedule and created after the previous occurrence
                last_runs = Task.objects.filter(new_schedule=schedule, created_at__gt=schedule.recurrences.before(now))


                if input_data:
                    # Join the input data targets into a large or-query, checking for task with any of the targets as input
                    filters = reduce(
                        operator.or_,
                        [Q(data__input_data__icontains=target) | Q(data__input_data=target) for target in input_data],
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
                    continue

            run_plugin_task(schedule.plugin.plugin_id, org.code, input_data, schedule.id)


def rerun_task(task: Task):
    plugin = Plugin.objects.get(plugin_id=task.data["plugin_id"])

    run_plugin_task(
        plugin.plugin_id, task.organization.code if task.organization else None, task.data["input_data"], None
    )


def run_plugin_task(
    plugin_id: str,
    organization_code: str | None = None,
    input_data: str | list[str] | set[str] | None = None,
    schedule_id: int | None = None,
) -> None:
    if isinstance(input_data, set):
        input_data = list(input_data)

    task_id = uuid.uuid4()
    Task.objects.create(
        id=task_id,
        type="plugin",
        new_schedule_id=schedule_id,
        organization=Organization.objects.get(code=organization_code) if organization_code else None,
        status=TaskStatus.QUEUED,
        data={"plugin_id": plugin_id, "input_data": input_data},  # TODO
    )

    app.send_task("tasks.new_tasks.run_plugin", (plugin_id, organization_code, input_data), task_id=str(task_id))


@app.task(bind=True)
def run_plugin(
    self, plugin_id: str, organization_code: str | None = None, input_data: str | list[str] | None = None
) -> None:
    logger.debug(
        "Starting task plugin",
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
        task.ended_at = datetime.now(timezone.utc)
        task.save()
    except:
        task.status = TaskStatus.FAILED
        task.ended_at = datetime.now(timezone.utc)
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
