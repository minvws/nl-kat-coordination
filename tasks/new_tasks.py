import uuid
from datetime import datetime, timedelta, timezone

import structlog
from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Coalesce

from files.models import File
from katalogus.models import NormalizerConfig, Normalizer as NormalizerDB
from katalogus.worker.job_models import NormalizerMeta, RawData, BoefjeMeta
from katalogus.worker.models import Normalizer
from katalogus.worker.repository import get_local_repository
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
        task_id = uuid.uuid4()
        task = Task.objects.create(
            id=task_id,
            type="plugin",
            organization=enabled_plugin.organization,
            status=TaskStatus.QUEUED,
            data={},  # TODO
        )
        app.send_task(
            "tasks.tasks.run_plugin",
            (task.organization.code, enabled_plugin.plugin.plugin_id, ooi.reference),
            task_id=str(task.id),
        )
        count += 1

    logger.info("Finished scheduling %s plugins", count)


@app.task(bind=True)
def run_plugin(self, organization: str, plugin_id: str, input_ooi: str) -> None:
    # TODO: remove need to create task beforehand
    logger.info("Starting task %s for plugin [org=%s, plugin_id=%s]", self.request.id, organization, plugin_id)

    plugin = (
        Plugin.objects.filter(plugin_id=plugin_id)
        .filter(Q(enabled_plugins__organization=Organization.objects.get(code=organization)) | Q(enabled_plugins__isnull=True))
        .annotate(enabled=Coalesce("enabled_plugins__enabled", False), enabled_id=Coalesce("enabled_plugins__id", None))
        .first()
    )

    if not plugin or not plugin.enabled:
        raise RuntimeError("Plugin is not enabled")

    scheduler_task = Task.objects.get(id=self.request.id)
    scheduler_task.status = TaskStatus.RUNNING
    scheduler_task.save()

    runner = PluginRunner()

    try:
        # TODO: run plugin on multiple oois?
        runner.run(plugin_id, input_ooi)
    except:
        Task.objects.filter(id=self.request.id).update(status=TaskStatus.FAILED)
        raise

    logger.info("dispatching raw files")

    for file in File.objects.filter(task_result__task_id=self.request.id):
        app.send_task("tasks.tasks.process_raw", (str(file.id),))

    logger.info("Handled plugin [org=%s, plugin_id=%s]", organization, plugin_id)


@app.task
def process_raw(raw_file_id: int, handle_error: bool = False) -> None:
    logger.info("Handling raw file %s", raw_file_id)
    file = File.objects.get(id=raw_file_id)

    return process_raw_file(file, handle_error)


def process_raw_file(file: File, handle_error: bool = False):
    if file.type == "error" and not handle_error:
        logger.info("Raw file %s contains an exception trace and handle_error is set to False. Skipping.", file.id)
        return

    # TODO:
    #  - Find enabled Plugins that should be triggered based on new trigger fields/logic
    #  - Run fast scripts directly with: run_plugin.apply(...)
    #  - Run involved tasks async
