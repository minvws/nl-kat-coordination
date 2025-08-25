from datetime import datetime, timedelta, timezone

import structlog
from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Coalesce

from files.models import File
from octopoes.models import OOI, ScanLevel
from octopoes.models.exception import TypeNotFound
from octopoes.models.types import type_by_name
from openkat.models import Organization
from plugins.models import EnabledPlugin, Plugin
from plugins.runner import PluginRunner
from tasks.celery import app
from tasks.models import Task, TaskStatus

logger = structlog.get_logger(__name__)


@app.task(queue=settings.QUEUE_NAME_SCHEDULE)
def schedule():
    pass  # TODO: check recurrence field


def get_expired_plugins(
    plugin_id: str | None = None, input_oois: list[str] | None = None, organization: str | None = None
) -> list[tuple[OOI, EnabledPlugin]]:
    # TODO: base this query on the new recurrence field
    recent_tasks = Task.objects.filter(
        created_at__gte=datetime.now(timezone.utc) - timedelta(minutes=settings.GRACE_PERIOD), type="plugin"
    ).all()

    enabled_plugins = EnabledPlugin.objects.filter(enabled=True)

    if organization:
        enabled_plugins = enabled_plugins.filter(organization__code=organization)

    oois = None
    expired: list[tuple[OOI, EnabledPlugin]] = []

    if plugin_id:
        enabled_plugins = enabled_plugins.filter(plugin__plugin_id=plugin_id)
    if input_oois is not None and organization:
        connector = settings.OCTOPOES_FACTORY(organization)
        oois = connector.load_objects_bulk(set(input_oois), datetime.now(timezone.utc)).values()

    for enabled_plugin in enabled_plugins:
        connector = settings.OCTOPOES_FACTORY(enabled_plugin.organization.code)
        consumes = set()

        for type_name in enabled_plugin.plugin.consumes:
            try:
                consumes.add(type_by_name(type_name))
            except TypeNotFound:
                logger.warning("Unknown OOI type %s for plugin consumes %s", type_name, enabled_plugin.plugin.plugin_id)

        scan_levels = {scan_level for scan_level in ScanLevel if scan_level.value >= enabled_plugin.plugin.scan_level}

        if oois:
            oois = [o for o in oois if o.scan_profile.level in scan_levels]
        else:
            oois = connector.list_objects(consumes, datetime.now(timezone.utc), scan_level=scan_levels).items

        for ooi in oois:
            if recent_tasks.filter(
                data__input_ooi=ooi.primary_key,
                organization=enabled_plugin.organization,
                data__plugin__id=enabled_plugin.plugin.id,
            ).exists():
                logger.debug(
                    "Recent task found, skipping dispatch or plugin %s for %s on %s",
                    enabled_plugin.plugin.plugin_id,
                    enabled_plugin.organization.code,
                    ooi.primary_key,
                )
                continue

            expired.append((ooi, enabled_plugin))

    return expired


@app.task
def reschedule(
    plugin_id: str | None = None, input_oois: list[str] | None = None, organization: str | None = None
) -> None:
    logger.info("Scheduling plugins")
    count = 0
    for ooi, enabled_plugin in get_expired_plugins(plugin_id, input_oois, organization):
        app.send_task("tasks.tasks.run_plugin", (enabled_plugin.plugin.plugin_id, enabled_plugin.organization, ooi))
        count += 1

    logger.info("Finished scheduling %s plugins", count)


@app.task(bind=True)
def run_plugin(self, plugin_id: str, organization: str | None = None, input_data: str | None = None) -> None:
    # TODO: remove need to create task beforehand
    logger.info("Starting task %s for plugin [org=%s, plugin_id=%s]", self.request.id, organization, plugin_id)

    task = Task.objects.create(
        id=self.request.id,
        type="plugin",
        organization=organization,
        status=TaskStatus.RUNNING,
        data={},  # TODO
    )

    org = None
    if organization:
        org = Organization.objects.get(code=organization)

    plugin = (
        Plugin.objects.filter(plugin_id=plugin_id)
        .filter(Q(enabled_plugins__organization=org) | Q(enabled_plugins__isnull=True))
        .annotate(enabled=Coalesce("enabled_plugins__enabled", False), enabled_id=Coalesce("enabled_plugins__id", None))
        .first()
    )

    if not plugin or not plugin.enabled:
        raise RuntimeError("Plugin is not enabled")

    try:
        PluginRunner().run(plugin_id, input_data)
        task.status = TaskStatus.COMPLETED
        task.save()
    except:
        task.status = TaskStatus.FAILED
        task.save()
        raise

    logger.info("Handled plugin [org=%s, plugin_id=%s]", organization, plugin_id)


def process_raw_file(file: File, handle_error: bool = False):
    if file.type == "error" and not handle_error:
        logger.info("Raw file %s contains an exception trace and handle_error is set to False. Skipping.", file.id)
        return

    for plugin in Plugin.objects.filter(consumes__contains=[f"file:{file.type}"]):
        run_plugin.apply_async((plugin.plugin_id,), kwargs={"input_data": str(file.id)})
