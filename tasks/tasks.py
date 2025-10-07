import operator
import uuid
from datetime import UTC, datetime
from functools import reduce

import celery
import structlog
from celery import Celery
from django.conf import settings
from django.db import OperationalError, connections
from django.db.models import Max, OuterRef, Q, Subquery
from djangoql.queryset import apply_search

from files.models import File
from objects.models import (
    DNSAAAARecord,
    DNSARecord,
    DNSCNAMERecord,
    DNSNSRecord,
    Hostname,
    IPAddress,
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


def recalculate_scan_profiles() -> list[ScanLevel]:
    """
    These are the currently implemented rules for Scan Profile:
      - For all DNSRecords, the hostname field has max_inherit_scan_level=2
      - For all DNSMXRecords, the mail_server field has max_inherit_scan_level=1
      - For all DNSNSRecords, the name_server field has max_issue_scan_level=1
      - For all DNSCNAMERecords, the hostname field has max issue/inherit=4
      - Through ResolvedHostname, ip addresses get the same level as the hostname
      - For IPPort the address field has max_inherit_scan_level=4 -> makes no sense: we can take the address's level
      - TODO: For IPAddress the netblock field has max_inherit_scan_level=4 -> same as above

      But there are no plugins that scan dns records. So, we could simplify this by implementing these rules:
      - For DNSArecords, take the max of the ip's scan level and hostname's scan level
      - For DNSNSrecords, set the target's scan level to the hostname's scan level, with a max of 1
      - For DNSCNAMERecords, set the target's scan level to the hostname's scan level

      This reduces the number of queries from 10 to 4 and requires less recursive iterations. Note that MX records are
      a "sink" in the sense that they do not issue scan levels, but are also not a scan target, so we can skip them.
    """
    updates: list[ScanLevel] = []

    # These could create an endless chain, but we just rely on multiple iterations to resolve this.
    updates.extend(sync_cname_scan_levels())
    updates.extend(sync_ns_scan_levels())
    updates.extend(sync_hostname_ip_scan_levels(DNSARecord._meta.db_table))
    updates.extend(sync_hostname_ip_scan_levels(DNSAAAARecord._meta.db_table))

    logger.info("Recalculating %s Scan Profiles", len(updates))

    bulk_insert(updates)
    logger.info("Recalculated %s Scan Profiles", len(updates))

    return updates


def sync_hostname_ip_scan_levels(db_table: str) -> list[ScanLevel]:
    # TODO: test multiple a records with same ip addresses and hostnames

    try:
        with connections["xtdb"].cursor() as cursor:
            cursor.execute(
                f"""SELECT
                CASE
                    WHEN host_level.scan_level IS NULL or ip_level.scan_level IS NULL THEN NULL
                    WHEN host_level.scan_level > ip_level.scan_level THEN ip_level._id
                    WHEN ip_level.scan_level > host_level.scan_level THEN host_level._id
                END AS id,
                CASE
                    WHEN host_level.scan_level IS NULL THEN hostname._id
                    WHEN ip_level.scan_level IS NULL THEN ip._id
                    WHEN host_level.scan_level > ip_level.scan_level THEN ip._id
                    WHEN host_level.scan_level < ip_level.scan_level THEN hostname._id
                END AS object_id,
                CASE
                    WHEN host_level.scan_level IS NULL THEN 'hostname'
                    WHEN ip_level.scan_level IS NULL THEN 'ipaddress'
                    WHEN host_level.scan_level > ip_level.scan_level THEN 'ipaddress'
                    WHEN host_level.scan_level < ip_level.scan_level THEN 'hostname'
                END AS object_type,
                COALESCE(
                    GREATEST(host_level.scan_level, ip_level.scan_level),
                    host_level.scan_level,
                    ip_level.scan_level
                ) AS scan_level,
                FALSE AS declared,
                COALESCE(host_level.organization_id, ip_level.organization_id) as organization_id,
                NULL AS last_changed_by
            FROM {db_table} dns
                JOIN {Hostname._meta.db_table} hostname ON hostname._id = dns.hostname_id
                LEFT JOIN {ScanLevel._meta.db_table} host_level ON host_level.object_id = hostname._id
                JOIN {IPAddress._meta.db_table} ip ON ip._id = dns.ip_address_id
                LEFT JOIN {ScanLevel._meta.db_table} ip_level ON ip_level.object_id = ip._id
            WHERE
                (
                    (host_level._id IS NULL OR host_level.declared is FALSE)
                    AND (ip_level._id IS NULL OR ip_level.declared is FALSE)
                ) AND
                (
                    (
                        host_level.scan_level IS NOT NULL
                        AND ip_level.scan_level IS NOT NULL
                        AND ip_level.scan_level != host_level.scan_level
                        AND ip_level.organization_id = host_level.organization_id
                    )
                    OR
                    (host_level.scan_level IS NOT NULL OR ip_level.scan_level IS NOT NULL)
            )
            """,  # noqa: S608
                {},
            )
            columns = [col[0] for col in cursor.description]
            update_or_creates = []
            for row in cursor.fetchall():
                kwargs = dict(zip(columns, row))

                if kwargs["object_id"] is None:
                    continue
                if kwargs["id"] is None:
                    del kwargs["id"]
                update_or_creates.append(ScanLevel(**kwargs))

            return update_or_creates
    except OperationalError:
        logger.error("Failed to perform scan level query", parent_model=Hostname, child_model=IPAddress)
        return []


def sync_ns_scan_levels() -> list[ScanLevel]:
    try:
        with connections["xtdb"].cursor() as cursor:
            cursor.execute(
                f"""SELECT
                    target_level._id AS id,
                    target._id AS object_id,
                    'hostname' AS object_type,
                    LEAST(Max(hostname_level.scan_level), 1) AS scan_level,
                    hostname_level.organization_id AS organization_id,
                    FALSE AS declared,
                    NULL AS last_changed_by
                FROM {DNSNSRecord._meta.db_table} dns
                    JOIN {Hostname._meta.db_table} hostname ON hostname._id = dns.hostname_id
                    JOIN {ScanLevel._meta.db_table} hostname_level ON hostname_level.object_id = hostname._id
                    JOIN {Hostname._meta.db_table} target ON target._id = dns.name_server_id
                    LEFT JOIN {ScanLevel._meta.db_table} target_level ON (
                    target_level.object_id = target._id
                    AND target_level.organization_id = hostname_level.organization_id
                )
                WHERE hostname_level.scan_level IS NOT NULL
                AND (
                    target_level._id IS NULL OR
                    (target_level.declared IS FALSE AND target_level.scan_level < LEAST(hostname_level.scan_level, 1))
                    )
            """,  # noqa: S608
                {},
            )
            columns = [col[0] for col in cursor.description]
            update_or_creates = []
            for row in cursor.fetchall():
                kwargs = dict(zip(columns, row))

                if kwargs["id"] is None:
                    del kwargs["id"]
                update_or_creates.append(ScanLevel(**kwargs))

            return update_or_creates
    except OperationalError:
        logger.error("Failed to perform scan level query", parent_model=Hostname, child_model=IPAddress)
        return []


def sync_cname_scan_levels() -> list[ScanLevel]:
    try:
        with connections["xtdb"].cursor() as cursor:
            cursor.execute(
                f"""SELECT
                target_level._id AS id,
                target._id AS object_id,
                'hostname' AS object_type,
                Max(hostname_level.scan_level) AS scan_level,
                hostname_level.organization_id AS organization_id,
                FALSE AS declared,
                NULL AS last_changed_by
                FROM {DNSCNAMERecord._meta.db_table} dns
                    JOIN {Hostname._meta.db_table} hostname ON hostname._id = dns.target_id
                    JOIN {ScanLevel._meta.db_table} hostname_level ON hostname_level.object_id = hostname._id
                    JOIN {Hostname._meta.db_table} target ON target._id = dns.hostname_id
                    LEFT JOIN {ScanLevel._meta.db_table} target_level ON (
                        target_level.object_id = target._id
                        AND target_level.organization_id = hostname_level.organization_id
                    )
                WHERE hostname_level.scan_level IS NOT NULL
                AND (
                    target_level._id IS NULL
                    OR (target_level.declared IS FALSE AND hostname_level.scan_level > target_level.scan_level)
                )""",  # noqa: S608
                {},
            )
            columns = [col[0] for col in cursor.description]
            update_or_creates = []
            for row in cursor.fetchall():
                kwargs = dict(zip(columns, row))

                if kwargs["object_id"] is None:
                    continue
                if kwargs["id"] is None:
                    del kwargs["id"]
                update_or_creates.append(ScanLevel(**kwargs))

            return update_or_creates
    except OperationalError:
        logger.error("Failed to perform scan level query", parent_model=Hostname, child_model=IPAddress)
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
        # Dynamic mode: query objects of the specified type, optionally filtered by query,
        # then filter by scan level
        model_class = schedule.object_set.object_type.model_class()
        model_qs = model_class.objects.all()

        if schedule.object_set.object_query:
            model_qs = apply_search(model_qs, schedule.object_set.object_query)

        subquery = Subquery(
            ScanLevel.objects.filter(
                object_type=model_class.__name__.lower(), object_id=OuterRef("id"), organization=organization.pk
            )
            .values("object_id")
            .annotate(
                max_scan_level=Max("scan_level")
            )  # Take the because we need a level at least the plugin.scan_level
            .values("max_scan_level")
        )
        model_qs = model_qs.annotate(max_scan_level=subquery).filter(max_scan_level__gte=schedule.plugin.scan_level)
        input_data = input_data.union([str(model) for model in model_qs if str(model)])
    else:
        # Non-dynamic mode: use traverse_objects to get manually added objects,
        # objects from queries, and objects from subsets
        object_pks = schedule.object_set.traverse_objects()
        if object_pks:
            model_class = schedule.object_set.object_type.model_class()
            model_qs = model_class.objects.filter(pk__in=object_pks)
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

    # Get plugin to check for plugin-specific batch_size
    try:
        plugin = Plugin.objects.get(plugin_id=plugin_id)
        # Use plugin-specific batch_size if set, otherwise fall back to global setting
        batch_size = plugin.batch_size if plugin.batch_size is not None else settings.BATCH_SIZE
    except Plugin.DoesNotExist:
        # Fall back to global setting if plugin not found
        batch_size = settings.BATCH_SIZE

    if batch and isinstance(input_data, list) and batch_size > 0 and len(input_data) > batch_size:
        tasks = []
        idx = 0

        for idx_2 in range(batch_size, len(input_data) + batch_size, batch_size):
            tasks.append(
                run_plugin_task(
                    plugin_id, organization_code, input_data[idx:idx_2], schedule_id, batch=False, celery=celery
                )[0]
            )
            idx = idx_2

        logger.info("Created %s batched tasks of batch size %s", len(tasks), batch_size)
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


def process_raw_file(file: File, handle_error: bool = False, celery: Celery = app) -> list[Task]:
    if file.type == "error" and not handle_error:
        logger.info("Raw file %s contains an exception trace and handle_error is set to False. Skipping.", file.id)
        return []

    tasks = []

    if hasattr(file, "task_result") and file.task_result is not None:
        organization = file.task_result.task.organization

        for plugin in Plugin.objects.filter(consumes__contains=[f"file:{file.type}"]):
            if plugin.enabled_for(organization):
                tasks.extend(
                    run_plugin_task(
                        plugin.plugin_id, organization.code if organization else None, str(file.id), celery=celery
                    )
                )

        return tasks

    for plugin in Plugin.objects.filter(consumes__contains=[f"file:{file.type}"]):
        for enabled_org in plugin.enabled_organizations():
            tasks.extend(run_plugin_task(plugin.plugin_id, enabled_org.code, str(file.id), celery=celery))

    return tasks
