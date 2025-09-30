import operator
import uuid
from datetime import UTC, datetime
from functools import reduce

import celery
import structlog
from celery import Celery
from django.conf import settings
from django.db import OperationalError, connections
from django.db.models import Max, Model, OuterRef, Q, Subquery
from djangoql.queryset import apply_search

from files.models import File
from objects.models import (
    DNSAAAARecord,
    DNSARecord,
    DNSCAARecord,
    DNSCNAMERecord,
    DNSMXRecord,
    DNSNSRecord,
    DNSPTRRecord,
    DNSSRVRecord,
    DNSTXTRecord,
    Hostname,
    IPAddress,
    IPPort,
    ScanLevel,
    bulk_insert,
)
from openkat.models import Organization
from plugins.models import Plugin
from plugins.runner import PluginRunner
from tasks.celery import app
from tasks.models import Schedule, Task, TaskStatus

logger = structlog.get_logger(__name__)


@app.task(queue=settings.QUEUE_NAME_SCAN_PROFILES)
def schedule_scan_profile_recalculations():
    recalculate_scan_profiles()


def recalculate_scan_profiles(depth: int = 0) -> None:
    """
    These are the currently implemented rules for Scan Profile:
      - For all DNSRecords, the hostname field has max_inherit_scan_level=2
      - For all DNSMXRecords, the mail_server field has max_inherit_scan_level=1
      - For all DNSNSRecords, the name_server field has max_issue_scan_level=1
      - For IPPort the address field has max_inherit_scan_level=4
      - TODO: For IPAddress the netblock field has max_inherit_scan_level=4 (if/once a netblock has been reintroduced)
    """
    updates = []

    for model in [DNSARecord, DNSAAAARecord, DNSPTRRecord, DNSCNAMERecord, DNSCAARecord, DNSTXTRecord, DNSSRVRecord]:
        updates.extend(calculate_updates(Hostname, model, relation="hostname_id", max_inherit=2))

    updates.extend(calculate_updates(DNSNSRecord, Hostname, relation="name_server_id", max_inherit=1, from_parent=True))
    updates.extend(calculate_updates(Hostname, DNSMXRecord, relation="mail_server_id", max_inherit=1))
    updates.extend(calculate_updates(IPAddress, IPPort, relation="address_id", max_inherit=4))

    if not updates:
        return

    bulk_insert(updates)

    if depth < 10:  # We could have an infinite recursion path: Hostname -> NS -> Hostname -> NS -> ...
        recalculate_scan_profiles(depth + 1)


def calculate_updates(
    parent_model: type[Model], child_model: type[Model], max_inherit: int, relation: str, from_parent: bool = False
) -> list[ScanLevel]:
    on_clause = f"parent._id = child.{relation}" if not from_parent else f"parent.{relation} = child._id"

    try:
        updates = list(
            ScanLevel.objects.raw(
                f"""
                SELECT child_level._id, child_level.declared, child_level.last_changed_by, child_level.object_id,
                child_level.object_type, child_level.organization_id,
                LEAST(MAX(parent_level.scan_level), %(max_inherit)s) AS scan_level
                FROM {ScanLevel._meta.db_table} child_level
                JOIN {child_model._meta.db_table} child ON child._id = child_level.object_id
                JOIN {parent_model._meta.db_table} parent ON {on_clause}
                JOIN {ScanLevel._meta.db_table} parent_level ON (
                    parent_level.object_id = parent._id AND parent_level.organization_id = child_level.organization_id
                )
                WHERE child_level.scan_level < %(max_inherit)s
                AND parent_level.scan_level > child_level.scan_level
                AND child_level.declared = false
            """,  # noqa: S608
                {"max_inherit": max_inherit},
            )
        )
        with connections["xtdb"].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT false as declared, null as last_changed_by,
                child._id as object_id, %(object_type)s as object_type, parent_level.organization_id as organization_id,
                LEAST(MAX(parent_level.scan_level), %(max_inherit)s) AS scan_level
                FROM {ScanLevel._meta.db_table} parent_level
                JOIN {parent_model._meta.db_table} parent ON parent._id = parent_level.object_id
                JOIN {child_model._meta.db_table} child ON {on_clause}
                LEFT JOIN {ScanLevel._meta.db_table} child_level ON (
                    child_level.object_id = child._id AND child_level.organization_id = parent_level.organization_id
                )
                WHERE child_level._id is null
            """,  # noqa: S608
                {"max_inherit": max_inherit, "object_type": child_model.__name__.lower()},
            )
            columns = [col[0] for col in cursor.description]
            inserts = [ScanLevel(**dict(zip(columns, row))) for row in cursor.fetchall()]
        return updates + inserts
    except OperationalError:
        logger.error("Failed to perform scan level query", parent_model=parent_model, child_model=child_model)
        return []


@app.task(queue=settings.QUEUE_NAME_SCHEDULE)
def reschedule() -> None:
    logger.info("Scheduling plugins")

    for schedule in Schedule.objects.filter(enabled=True):
        run_schedule(schedule, force=False)

    logger.info("Finished scheduling plugins")


def run_schedule(schedule: Schedule, force: bool = True, celery: Celery = app) -> list[Task]:
    if not schedule.plugin:
        logger.debug("No plugin defined for schedule, skipping")
        return []

    orgs = schedule.plugin.enabled_organizations() if not schedule.organization else [schedule.organization]
    tasks = []

    for org in orgs:
        tasks.extend(run_schedule_for_organization(schedule, org, force, celery=celery))

    return tasks


def run_schedule_for_organization(
    schedule: Schedule, organization: Organization, force: bool = True, celery: Celery = app
) -> list[Task]:
    now = datetime.now(UTC)

    if not schedule.object_set:
        if force:
            return run_plugin_task(schedule.plugin.plugin_id, organization.code, None, schedule.id, celery=celery)

        last_run = Task.objects.filter(schedule=schedule, data__input_data=None).order_by("-created_at").first()
        if last_run and not schedule.recurrences.between(last_run.created_at, now):
            logger.debug("Plugin '%s' has already run recently", schedule.plugin.plugin_id)
            return []

        return run_plugin_task(schedule.plugin.plugin_id, organization.code, None, schedule.id, celery=celery)

    input_data: set[str] = set()

    if schedule.object_set.object_query is not None and schedule.object_set.dynamic is True:
        model_qs = schedule.object_set.object_type.model_class().objects.all()

        if schedule.object_set.object_query:
            model_qs = apply_search(model_qs, schedule.object_set.object_query)

        subquery = Subquery(
            ScanLevel.objects.filter(
                object_type=schedule.object_set.object_type.model_class().__name__,
                object_id=OuterRef("id"),
                organization=organization.pk,
            )
            .values("object_id")
            .annotate(
                max_scan_level=Max("scan_level")
            )  # Take the because we need a level at least the plugin.scan_level
            .values("max_scan_level")
        )
        model_qs = model_qs.annotate(max_scan_level=subquery).filter(max_scan_level__gte=schedule.plugin.scan_level)
        input_data = input_data.union([str(model) for model in model_qs if str(model)])

    if not input_data:
        return []

    if force:
        return run_plugin_task(schedule.plugin.plugin_id, organization.code, input_data, schedule.id, celery=celery)

    # Filter on the schedule and created after the previous occurrence
    last_runs = Task.objects.filter(schedule=schedule, created_at__gt=schedule.recurrences.before(now))

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
        return []

    return run_plugin_task(schedule.plugin.plugin_id, organization.code, input_data, schedule.id, celery=celery)


def rerun_task(task: Task, celery: Celery = app) -> list[Task]:
    plugin = Plugin.objects.get(plugin_id=task.data["plugin_id"])

    return run_plugin_task(
        plugin.plugin_id,
        task.organization.code if task.organization else None,
        task.data["input_data"],
        None,
        celery=celery,
    )


def run_plugin_task(
    plugin_id: str,
    organization_code: str | None = None,
    input_data: str | list[str] | set[str] | None = None,
    schedule_id: int | None = None,
    batch: bool = True,
    celery: Celery = app,
) -> list[Task]:
    if isinstance(input_data, set):
        input_data = list(input_data)

    if batch and isinstance(input_data, list) and settings.BATCH_SIZE > 0 and len(input_data) > settings.BATCH_SIZE:
        tasks = []
        idx = 0

        for idx_2 in range(settings.BATCH_SIZE, len(input_data) + settings.BATCH_SIZE, settings.BATCH_SIZE):
            tasks.append(
                run_plugin_task(plugin_id, organization_code, input_data[idx:idx_2], batch=False, celery=celery)[0]
            )
            idx = idx_2

        return tasks

    task_id = uuid.uuid4()
    task = Task.objects.create(
        id=task_id,
        type="plugin",
        schedule_id=schedule_id,
        organization=Organization.objects.get(code=organization_code) if organization_code else None,
        status=TaskStatus.QUEUED,
        data={"plugin_id": plugin_id, "input_data": input_data},  # TODO
    )

    run_plugin.bind(celery)  # Make sure to bind the right celery instance to be able to test these tasks.
    async_result = run_plugin.apply_async((plugin_id, organization_code, input_data), task_id=str(task_id))
    task._async_result = async_result

    return [task]


@app.task(bind=True)
def run_plugin(
    self: celery.Task, plugin_id: str, organization_code: str | None = None, input_data: str | list[str] | None = None
) -> str:
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
        out = PluginRunner().run(plugin_id, input_data, task_id=task.id)
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
    return out


def process_raw_file(file: File, handle_error: bool = False, celery: Celery = app) -> None:
    if file.type == "error" and not handle_error:
        logger.info("Raw file %s contains an exception trace and handle_error is set to False. Skipping.", file.id)
        return

    for plugin in Plugin.objects.filter(consumes__contains=[f"file:{file.type}"]):
        for organization in plugin.enabled_organizations():
            run_plugin_task(plugin.plugin_id, organization.code, str(file.id), celery=celery)
