import time
import uuid
from datetime import UTC, datetime

import celery
import structlog
from celery import Celery
from django.conf import settings
from django.core.cache import caches
from django.db import OperationalError, connections
from djangoql.queryset import apply_search
from redis.exceptions import LockError  # type: ignore

from files.models import File
from objects.models import DNSAAAARecord, DNSARecord, DNSCNAMERecord, DNSNSRecord, Hostname, IPAddress
from openkat.models import Organization, User
from plugins.models import BusinessRule, Plugin
from plugins.plugins.business_rules import run_rules
from plugins.runner import PluginRunner
from reports.generator import ReportPDFGenerator
from tasks.celery import app
from tasks.models import ObjectSet, Schedule, Task, TaskResult, TaskStatus

logger = structlog.get_logger(__name__)


@app.task(queue=settings.QUEUE_NAME_RECALCULATIONS)
def schedule_scan_profile_recalculations():
    try:
        # Create a Lock to:
        #   1. Avoid running several recalculation scripts at the same time and burn down the database
        #   2. Still take into account that there might be anomalies when a large set of objects has been changed
        with caches["default"].lock(
            "recalculate_scan_levels", blocking=False, timeout=10 * settings.SCAN_LEVEL_RECALCULATION_INTERVAL
        ):
            recalculate_scan_levels()
    except LockError:
        logger.warning("Scan level calculation is running, consider increasing SCAN_LEVEL_RECALCULATION_INTERVAL")


@app.task(queue=settings.QUEUE_NAME_RECALCULATIONS)
def schedule_business_rule_recalculations(from_trigger: bool = False) -> None:
    try:
        # Create a Lock that lives for three times the settings.SCAN_LEVEL_RECALCULATION_INTERVAL at most, to:
        #   1. Avoid running several recalculation scripts at the same time and burn down the database
        #   2. Still take into account that there might be anomalies when a large set of objects has been changed
        with caches["default"].lock(
            "recalculate_business_rules", blocking=False, timeout=10 * settings.BUSINESS_RULE_RECALCULATION_INTERVAL
        ):
            if from_trigger:
                # If a plugin posts hostname updates, this task gets scheduled. But potentially that plugin also posts
                # DNS updates 200ms later. If we run recalculations before that, we miss the DNS updates as the lock
                # makes sure we skip later updates.
                logger.info("Delaying recalculation to potentially fill a batch of updates in one run...")
                time.sleep(5)

            run_rules(BusinessRule.objects.filter(enabled=True), False)
    except LockError:
        if not from_trigger:
            logger.warning(
                "Business rule calculation is running, consider increasing BUSINESS_RULE_RECALCULATION_INTERVAL"
            )
        else:
            logger.debug(
                "Business rule calculation is running, consider increasing BUSINESS_RULE_RECALCULATION_INTERVAL"
            )


@app.task(queue=settings.QUEUE_NAME_RECALCULATIONS)
def run_business_rules(business_rule_ids: list[int]) -> None:
    for business_rule_id in business_rule_ids:
        try:
            business_rule = BusinessRule.objects.get(pk=business_rule_id)
            logger.info("Running business rule: %s", business_rule.name)
            run_rules([business_rule], False)
            logger.info("Completed business rule: %s", business_rule.name)
        except BusinessRule.DoesNotExist:
            logger.error("Business rule %s not found", business_rule_id)
        except Exception:
            logger.exception("Error running business rule %s", business_rule_id)


def recalculate_scan_levels():
    """
    Recalculate scan levels based on DNS relationships:
      - For DNSArecords, sync hostname scan level with IP address scan level (bidirectional)
      - For DNSNSrecords, set the name server's scan level to the hostname's scan level, with a max of 1
      - For DNSCNAMERecords, set the target's scan level to the hostname's scan level

    These updates respect the 'declared' flag - only non-declared scan levels are updated.
    """
    logger.info("Recalculating Scan Profiles...")

    # These could create an endless chain, but we just rely on multiple iterations to resolve this.
    sync_cname_scan_levels()
    sync_ns_scan_levels()
    sync_hostname_ip_scan_levels(DNSARecord._meta.db_table)
    sync_hostname_ip_scan_levels(DNSAAAARecord._meta.db_table)

    logger.info("Recalculated Scan Profiles")


def sync_hostname_ip_scan_levels(db_table: str) -> None:
    """
    Synchronize scan levels between hostnames and IP addresses based on DNS A/AAAA records.
    Returns the number of objects updated.
    """
    try:
        with connections["xtdb"].cursor() as cursor:
            # Update IPs where hostname has higher scan level and IP is not declared
            cursor.execute(
                f"""
                INSERT INTO {IPAddress._meta.db_table} (_id, address, network_id, scan_level, declared)
                select target._id, target.address, target.network_id, source.scan_level, false
                FROM {Hostname._meta.db_table} source
                JOIN {db_table} dns on source._id = dns.hostname_id
                JOIN {IPAddress._meta.db_table}
                target ON target._id = dns.ip_address_id
                WHERE source.scan_level IS NOT NULL AND target.declared IS FALSE
                AND (target.scan_level is null or target.scan_level < source.scan_level);
                """  # noqa: S608
            )

            # Update hostnames where IP has higher scan level and hostname is not declared
            cursor.execute(
                f"""
                INSERT INTO {Hostname._meta.db_table} (_id, address, network_id, scan_level, declared)
                select target._id, target.address, target.network_id, source.scan_level, false
                FROM {IPAddress._meta.db_table} source
                JOIN {db_table} dns on source._id = dns.ip_address_id
                JOIN {Hostname._meta.db_table} target ON target._id = dns.hostname_id
                WHERE source.scan_level IS NOT NULL AND target.declared IS FALSE
                AND (target.scan_level is null or target.scan_level < source.scan_level);
                """  # noqa: S608
            )
    except OperationalError:
        logger.exception("Failed to perform scan level query", parent_model=Hostname, child_model=IPAddress)


def sync_ns_scan_levels() -> None:
    """
    Sync scan levels to name servers via NS records.
    Name server scan level is set to the hostname's scan level, with a max of 1.
    Returns the number of objects updated.
    """
    try:
        with connections["xtdb"].cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {Hostname._meta.db_table} (_id, name, network_id, root, scan_level, declared)
                select target._id, target.name, target.network_id, target.root, LEAST(source.scan_level, 1), false
                FROM {Hostname._meta.db_table} source
                JOIN {DNSNSRecord._meta.db_table} dns on source._id = dns.hostname_id
                JOIN {Hostname._meta.db_table} target ON target._id = dns.name_server_id
                WHERE source.scan_level IS NOT NULL AND target.declared IS FALSE
                AND (target.scan_level is null or  target.scan_level != LEAST(source.scan_level, 1));
                """  # noqa: S608
            )
    except OperationalError:
        logger.exception("Failed to perform NS scan level query")


def sync_cname_scan_levels() -> None:
    """
    Sync scan levels to CNAME targets.
    Target hostname scan level is set to the max of all source hostname scan levels.
    Returns the number of objects updated.
    """
    try:
        with connections["xtdb"].cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {Hostname._meta.db_table} (_id, name, network_id, root, scan_level, declared)
                select target._id, target.name, target.network_id, target.root, source.scan_level, false
                FROM {Hostname._meta.db_table} source
                JOIN {DNSCNAMERecord._meta.db_table} dns on source._id = dns.target_id
                JOIN {Hostname._meta.db_table} target ON target._id = dns.hostname_id
                WHERE source.scan_level IS NOT NULL AND target.declared IS FALSE
                AND target.scan_level is null or  target.scan_level != source.scan_level;
                """  # noqa: S608
            )
    except OperationalError:
        logger.exception("Failed to perform CNAME scan level query")


@app.task(queue=settings.QUEUE_NAME_SCHEDULE)
def reschedule() -> None:
    logger.info("Scheduling plugins")
    tasks = []

    for schedule in Schedule.objects.filter(enabled=True):
        tasks.extend(run_schedule(schedule, force=False))

    logger.info("Finished scheduling %s plugins", len(tasks))


def run_schedule(schedule: Schedule, force: bool = True, celery: Celery = app) -> list[Task]:
    # Handle report tasks differently from plugin tasks
    if schedule.task_type == "report":
        return run_report_schedule(schedule, force, celery=celery)

    if not schedule.plugin:
        logger.debug("No plugin defined for schedule, skipping")
        return []

    return run_schedule_for_organization(schedule, schedule.organization, force, celery=celery)


def run_report_schedule(schedule: Schedule, force: bool = True, celery: Celery = app) -> list[Task]:
    now = datetime.now(UTC)

    # Check if we need to run based on recurrence rules
    if not force and schedule.recurrences:
        last_run = Task.objects.filter(schedule=schedule, type="report").order_by("-created_at").first()
        if last_run and not schedule.recurrences.between(last_run.created_at, now):
            logger.debug("Report schedule '%s' has already run recently", schedule.id)
            return []

    if schedule.organization:
        organization_codes = [schedule.organization.code]
    else:
        # If no specific organization, generate report for all organizations
        organization_codes = list(Organization.objects.values_list("code", flat=True))

    # Run the report task
    task = run_report_task(
        name=schedule.report_name or f"Scheduled Report {schedule.id}",
        description=schedule.report_description,
        organization_codes=organization_codes,
        finding_types=schedule.report_finding_types,
        object_set_id=schedule.object_set.id if schedule.object_set else None,
        schedule_id=schedule.id,
        celery=celery,
    )

    return [task]


def run_schedule_for_organization(
    schedule: Schedule, organization: Organization | None, force: bool = True, celery: Celery = app
) -> list[Task]:
    now = datetime.now(UTC)
    code = None if organization is None else organization.code

    if not schedule.object_set:
        if force:
            return run_plugin_task(schedule.plugin.plugin_id, code, None, schedule.pk, celery=celery)

        last_run = Task.objects.filter(schedule=schedule, data__input_data=None).order_by("-created_at").first()
        if last_run and not schedule.recurrences.between(last_run.created_at, now):
            logger.debug("Plugin '%s' has already run recently", schedule.plugin.plugin_id)
            return []

        return run_plugin_task(schedule.plugin.plugin_id, code, None, schedule.pk, celery=celery)

    input_data: set[str] = set()

    if schedule.object_set.object_query is not None and schedule.object_set.dynamic is True:
        # Dynamic mode: query objects of the specified type, optionally filtered by query,
        # then filter by scan level
        model_class = schedule.object_set.object_type.model_class()
        model_qs = model_class.objects.filter(scan_level__gte=schedule.plugin.scan_level)

        if schedule.object_set.object_query:
            model_qs = apply_search(model_qs, schedule.object_set.object_query)

        input_data = {str(model) for model in model_qs}
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
        return run_plugin_task(schedule.plugin.plugin_id, code, input_data, schedule.pk, celery=celery)

    # Filter on the schedule and created after the previous occurrence
    last_runs = Task.objects.filter(
        schedule=schedule, created_at__gt=schedule.recurrences.before(now), data__plugin_id=schedule.plugin.plugin_id
    )

    if input_data:
        for targets in last_runs.values_list("data__input_data", flat=True):
            input_data -= set(targets)

    if not input_data:
        return []

    return run_plugin_task(schedule.plugin.plugin_id, code, input_data, schedule.pk, celery=celery)


def rerun_task(task: Task, celery: Celery = app) -> list[Task]:
    # Handle different task types
    if task.type == "report":
        # Import here to avoid circular imports

        # Rerun report task with same parameters
        return [
            run_report_task(
                name=task.data.get("name", "Rerun Report"),
                description=task.data.get("description", ""),
                organization_codes=task.data.get("organization_codes", []),
                finding_types=task.data.get("finding_types", []),
                object_set_id=task.data.get("object_set_id"),
            )
        ]
    else:
        # Handle plugin tasks
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
    inputs: list[str] | None = None

    if isinstance(input_data, set):
        inputs = list(input_data)
    elif isinstance(input_data, str):
        inputs = [input_data]
    else:
        inputs = input_data

    # Get plugin to check for plugin-specific batch_size
    try:
        plugin = Plugin.objects.get(plugin_id=plugin_id)
        # Use plugin-specific batch_size if set, otherwise fall back to global setting
        batch_size = plugin.batch_size if plugin.batch_size is not None else settings.BATCH_SIZE
    except Plugin.DoesNotExist:
        # Fall back to global setting if plugin not found
        batch_size = settings.BATCH_SIZE

    if batch and isinstance(inputs, list) and batch_size > 0 and len(inputs) > batch_size:
        tasks = []
        idx = 0

        for idx_2 in range(batch_size, len(inputs) + batch_size, batch_size):
            tasks.append(
                run_plugin_task(
                    plugin_id, organization_code, inputs[idx:idx_2], schedule_id, batch=False, celery=celery
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
        data={"plugin_id": plugin_id, "input_data": inputs},  # TODO
    )

    run_plugin.bind(celery)  # Make sure to bind the right celery instance to be able to test these tasks.
    async_result = run_plugin.apply_async((plugin_id, organization_code, inputs), task_id=str(task_id))
    task._async_result = async_result

    return [task]


@app.task(bind=True)
def run_plugin(
    self: celery.Task, plugin_id: str, organization_code: str | None = None, input_data: list[str] | None = None
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

    if task.status == TaskStatus.CANCELLED:
        raise RuntimeError("Trying to run cancelled task")

    if organization_code:
        organization = Organization.objects.get(code=organization_code)

    plugin = Plugin.objects.filter(plugin_id=plugin_id).first()

    if not plugin:
        task.status = TaskStatus.FAILED
        task.save()
        raise RuntimeError(f"Plugin {plugin_id} not found")

    task.status = TaskStatus.RUNNING
    task.save()

    try:
        out = PluginRunner().run(plugin_id, input_data, task_id=task.pk)

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
        logger.info("Raw file %s contains an exception trace and handle_error is set to False. Skipping.", file.pk)
        return []

    tasks = []

    logger.info("Processing Raw file %s", file.pk)

    if hasattr(file, "task_result") and file.task_result is not None:
        organization = file.task_result.task.organization

        for plugin in Plugin.objects.filter(consumes__contains=[f"file:{file.type}"]):
            tasks.extend(
                run_plugin_task(
                    plugin.plugin_id, organization.code if organization else None, str(file.pk), celery=celery
                )
            )

        return tasks

    # For files without a task result, check all organizations with enabled schedules
    for plugin in Plugin.objects.filter(consumes__contains=[f"file:{file.type}"]):
        enabled_orgs = (
            Schedule.objects.filter(plugin=plugin, enabled=True).values_list("organization", flat=True).distinct()
        )

        # Check if there's a global schedule (organization=None)
        has_global_schedule = None in enabled_orgs

        if has_global_schedule:
            # If there's a global schedule, create tasks for all organizations
            for org in Organization.objects.all():
                tasks.extend(run_plugin_task(plugin.plugin_id, org.code, str(file.pk), celery=celery))
        else:
            # Otherwise, only create tasks for specific organizations
            for org_id in enabled_orgs:
                if org_id:
                    org = Organization.objects.get(pk=org_id)
                    tasks.extend(run_plugin_task(plugin.plugin_id, org.code, str(file.pk), celery=celery))

    return tasks


def run_report_task(
    name: str,
    description: str = "",
    organization_codes: list[str] | None = None,
    finding_types: list[str] | None = None,
    object_set_id: int | None = None,
    schedule_id: int | None = None,
    user_id: int | None = None,
    celery: Celery = app,
) -> Task:
    """Create and queue a report generation task"""
    task_id = uuid.uuid4()

    # Get the organization (for single org mode) - use first org if multiple
    organization = None
    if organization_codes and len(organization_codes) > 0:
        organization = Organization.objects.filter(code=organization_codes[0]).first()

    task = Task.objects.create(
        id=task_id,
        type="report",
        schedule_id=schedule_id,
        organization=organization,
        status=TaskStatus.QUEUED,
        data={
            "name": name,
            "description": description,
            "organization_codes": organization_codes or [],
            "finding_types": finding_types or [],
            "object_set_id": object_set_id,
            "user_id": user_id,
        },
    )

    create_report.bind(celery)
    async_result = create_report.apply_async(
        (name, description, organization_codes, finding_types, object_set_id, user_id), task_id=str(task_id)
    )
    task._async_result = async_result

    return task


@app.task(bind=True)
def create_report(
    self: celery.Task,
    name: str,
    description: str = "",
    organization_codes: list[str] | None = None,
    finding_types: list[str] | None = None,
    object_set_id: int | None = None,
    user_id: int | None = None,
) -> str:
    """Celery task for generating a report"""
    logger.info(
        "Starting report generation task", task_id=self.request.id, name=name, organization_codes=organization_codes
    )

    task = Task.objects.get(id=self.request.id)

    if task.status == TaskStatus.CANCELLED:
        raise RuntimeError("Trying to run cancelled task")

    task.status = TaskStatus.RUNNING
    task.save()

    try:
        # Get organizations if codes provided
        organizations = None
        if organization_codes:
            organizations = Organization.objects.filter(code__in=organization_codes)

        # Get object set if provided
        object_set = None
        if object_set_id:
            object_set = ObjectSet.objects.get(id=object_set_id)

        # Get user if provided
        user = None
        if user_id:
            user = User.objects.get(id=user_id)

        # Generate the report
        generator = ReportPDFGenerator(
            name=name,
            description=description,
            organizations=organizations,
            finding_types=finding_types,
            object_set=object_set,
            user=user,
        )
        report = generator.generate_pdf_report()

        # Create TaskResult to link file back to task
        TaskResult.objects.create(task=task, file=report.file)

        task.status = TaskStatus.COMPLETED
        task.ended_at = datetime.now(UTC)
        task.save()

        logger.info("Report generation completed successfully", task_id=self.request.id, report_id=report.id)
        return f"Report generated successfully: {report.id}"

    except Exception as e:
        task.refresh_from_db(fields=["status"])

        if task.status != TaskStatus.CANCELLED:
            task.status = TaskStatus.FAILED

        task.ended_at = datetime.now(UTC)
        task.save()

        logger.exception("Report generation failed", task_id=self.request.id, error=str(e))
        raise
