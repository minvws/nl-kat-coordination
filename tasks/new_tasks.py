from datetime import datetime, timezone

import structlog
from django.conf import settings

from files.models import File
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.exception import TypeNotFound
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

    for org in schedule.plugin.enabled_organizations():
        connector: OctopoesAPIConnector = settings.OCTOPOES_FACTORY(org.code)

        # TODO: will be replaced with direct(er) queries in XTDB 2.0
        if schedule.input:
            try:
                query = Query.from_path(schedule.input)
            except (ValueError, TypeNotFound):
                app.send_task(
                    "tasks.new_tasks.run_plugin", (schedule.plugin.plugin_id, org.code, schedule.input, schedule.id)
                )
                continue

            pk = Aliased(query.result_type, field="primary_key")

            objects = connector.octopoes.ooi_repository.query(
                query.find(pk).where(query.result_type, primary_key=pk), now
            )
            by_pk = {item[-1]: item[0] for item in objects}
            scan_profiles = connector.octopoes.scan_profile_repository.get_bulk([x for x in by_pk], now)

            for profile in scan_profiles:
                if profile.level.value < schedule.plugin.scan_level:
                    continue

                input_data = by_pk[str(profile.reference)]

                if not force:
                    last_run = (
                        Task.objects.filter(new_schedule=schedule, data__input_data=input_data)
                        .order_by("-created_at")
                        .first()
                    )
                    if last_run and not schedule.recurrences.between(last_run.created_at, now):
                        logger.debug("Plugin '%s' has already run recently", schedule.plugin.plugin_id)
                        continue

                app.send_task(
                    "tasks.new_tasks.run_plugin", (schedule.plugin.plugin_id, org.code, input_data, schedule.id)
                )
        else:
            last_run = Task.objects.filter(new_schedule=schedule, data__input_data=None).order_by("-created_at").first()
            if last_run and not schedule.recurrences.between(last_run.created_at, now):
                logger.debug("Plugin '%s' has already run recently", schedule.plugin.plugin_id)
                continue
            app.send_task("tasks.new_tasks.run_plugin", (schedule.plugin.plugin_id, org.code, None, schedule.id))


def rerun_task(task: Task):
    plugin = Plugin.objects.get(plugin_id=task.data["plugin_id"])

    app.send_task(
        "tasks.new_tasks.run_plugin",
        (plugin.plugin_id, task.organization.code if task.organization else None, task.data["input_data"], None),
    )


@app.task(bind=True)
def run_plugin(
    self,
    plugin_id: str,
    organization_code: str | None = None,
    input_data: str | None = None,
    schedule_id: int | None = None,
) -> None:
    logger.debug(
        "Starting task plugin",
        task_id=self.request.id,
        organization=organization_code,
        plugin_id=plugin_id,
        input_data=input_data,
    )
    organization: Organization | None = None

    if organization_code:
        organization = Organization.objects.get(code=organization_code)

    plugin = Plugin.objects.filter(plugin_id=plugin_id).first()

    if not plugin or not plugin.enabled_for(organization):
        raise RuntimeError(f"Plugin {plugin_id} is not enabled for {organization_code}")

    task = Task.objects.create(
        id=self.request.id,
        type="plugin",
        new_schedule_id=schedule_id,
        organization=organization,
        status=TaskStatus.RUNNING,
        data={"plugin_id": plugin_id, "input_data": input_data},  # TODO
    )

    try:
        PluginRunner().run(plugin_id, input_data, task_id=task.id)
        task.status = TaskStatus.COMPLETED
        task.save()
    except:
        task.status = TaskStatus.FAILED
        task.save()
        raise

    logger.info("Handled plugin", organization=organization, plugin_id=plugin_id, input_data=input_data)


def process_raw_file(file: File, handle_error: bool = False):
    if file.type == "error" and not handle_error:
        logger.info("Raw file %s contains an exception trace and handle_error is set to False. Skipping.", file.id)
        return

    for plugin in Plugin.objects.filter(consumes__contains=[f"file:{file.type}"]):
        for organization in plugin.enabled_organizations():
            run_plugin.apply_async((plugin.plugin_id, organization.code), kwargs={"input_data": str(file.id)})
