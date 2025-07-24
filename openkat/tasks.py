import base64
import gc
import timeit
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from croniter import croniter
from django.conf import settings
from django.db import transaction
from pydantic import TypeAdapter

from files.models import File, PluginContent
from katalogus.boefjes.boefje_handler import DockerBoefjeHandler
from katalogus.boefjes.normalizer_handler import LocalNormalizerHandler
from katalogus.models import BoefjeConfig, NormalizerConfig
from katalogus.models import Normalizer as NormalizerDB
from katalogus.worker.boefje_handler import LocalBoefjeHandler
from katalogus.worker.interfaces import BoefjeOutput, BoefjeStorageInterface
from katalogus.worker.interfaces import Task as WorkerTask
from katalogus.worker.job_models import BoefjeMeta, NormalizerMeta, RawData
from katalogus.worker.models import Boefje, Normalizer
from katalogus.worker.repository import get_local_repository
from octopoes.core.app import bootstrap_octopoes, get_xtdb_client
from octopoes.events.events import DBEvent, DBEventType
from octopoes.models import OOI, ScanLevel
from octopoes.models.exception import TypeNotFound
from octopoes.models.types import type_by_name
from octopoes.xtdb.client import XTDBSession
from openkat.celery import app
from openkat.models import Organization
from openkat.scheduler import scheduler_client
from reports.runner.models import ReportTask
from reports.runner.report_runner import LocalReportRunner
from tasks.models import Schedule, Task, TaskResult, TaskStatus

logger = structlog.get_logger(__name__)


@app.task(queue=settings.QUEUE_NAME_OCTOPOES)
def handle_event(event: dict) -> None:
    try:
        parsed_event: DBEvent = TypeAdapter(DBEventType).validate_python(event)

        session = XTDBSession(get_xtdb_client(settings.XTDB_URI, parsed_event.client))
        bootstrap_octopoes(parsed_event.client, session).process_event(parsed_event)
        session.commit()
    except Exception:
        logger.exception("Failed to handle event: %s", event)
        raise


@app.task(queue=settings.QUEUE_NAME_OCTOPOES)
def schedule_scan_profile_recalculations():
    orgs = Organization.objects.all()
    logger.info("Scheduling scan profile recalculation for %s organizations", len(orgs))

    for org in orgs:
        app.send_task(
            "openkat.tasks.recalculate_scan_profiles",
            (org.code,),
            queue=settings.QUEUE_NAME_OCTOPOES,
            task_id=str(uuid.uuid4()),
        )


@app.task(queue=settings.QUEUE_NAME_OCTOPOES)
def recalculate_scan_profiles(org: str, *args: Any, **kwargs: Any) -> None:
    session = XTDBSession(get_xtdb_client(settings.XTDB_URI, org))
    octopoes = bootstrap_octopoes(org, session)
    timer = timeit.default_timer()

    try:
        octopoes.recalculate_scan_profiles(datetime.now(timezone.utc))
        session.commit()
    except Exception:
        logger.exception("Failed recalculating scan profiles [org=%s] [dur=%.2fs]", org, timeit.default_timer() - timer)

    logger.info("Finished scan profile recalculation [org=%s] [dur=%.2fs]", org, timeit.default_timer() - timer)


class SimpleBoefjeStorageInterface(BoefjeStorageInterface):
    def save_output(self, boefje_meta: BoefjeMeta, boefje_output: BoefjeOutput) -> dict[str, uuid.UUID]:
        ids = {}

        with transaction.atomic():
            for file in boefje_output.files:
                raw_file = File.objects.create(
                    file=PluginContent(base64.b64decode(file.content), boefje_meta.boefje.plugin_id), type=file.type
                )
                ids[file.name] = raw_file.id
                TaskResult.objects.create(task_id=boefje_meta.id, file=raw_file)

        return ids


def next_run(expression: str, start_time: datetime | None = None) -> datetime:
    if start_time is None:
        start_time = datetime.now(timezone.utc)

    cron = croniter(expression, start_time)
    return cron.get_next(datetime)  # type: ignore


@app.task
def schedule():
    for schedule in Schedule.objects.filter(deadline_at__lte=datetime.now(timezone.utc), enabled=True):
        scheduler = scheduler_client(schedule.organization)
        task = Task.objects.create(
            id=uuid.uuid4(), type=schedule.type, organization=schedule.organization, data=schedule.data
        )
        scheduler.push_task(task)

        if schedule.schedule is None:  # One-off schedules
            schedule.deadline_at = None
        else:
            schedule.deadline_at = next_run(schedule.schedule)

        schedule.save()


def get_expired_boefjes(
    boefje_id: str | None = None, input_oois: list[str] | None = None, organization: str | None = None
) -> list[tuple[OOI, BoefjeConfig]]:
    recent_tasks = Task.objects.filter(
        created_at__gte=datetime.now(timezone.utc) - timedelta(minutes=settings.GRACE_PERIOD), type="boefje"
    ).all()
    configs = BoefjeConfig.objects.filter(enabled=True)

    if organization:
        configs = configs.filter(organization__code=organization)

    oois = None
    expired: list[tuple[OOI, BoefjeConfig]] = []

    if boefje_id:
        configs = configs.filter(boefje__plugin_id=boefje_id)
    if input_oois is not None and organization:
        connector = settings.OCTOPOES_FACTORY(organization)
        oois = connector.load_objects_bulk(set(input_oois), datetime.now(timezone.utc)).values()

    for config in configs:
        connector = settings.OCTOPOES_FACTORY(config.organization.code)
        consumes = set()

        for type_name in config.boefje.consumes:
            try:
                consumes.add(type_by_name(type_name))
            except TypeNotFound:
                logger.warning("Unknown OOI type %s for boefje consumes %s", type_name, boefje["id"])

        scan_levels = {scan_level for scan_level in ScanLevel if scan_level.value >= config.boefje.scan_level}

        if oois:
            oois = [o for o in oois if o.scan_profile.level in scan_levels]
        else:
            oois = connector.list_objects(consumes, datetime.now(timezone.utc), scan_level=scan_levels).items

        for ooi in oois:
            if recent_tasks.filter(
                data__input_ooi=ooi.primary_key, organization=config.organization, data__boefje__id=config.boefje.id
            ).exists():
                logger.debug(
                    "Recent task found, skipping dispatch or boefje %s for %s on %s",
                    config.boefje.plugin_id,
                    config.organization.code,
                    ooi.primary_key,
                )
                continue

            expired.append((ooi, config))

    return expired


@app.task
def reschedule(
    boefje_id: str | None = None, input_oois: list[str] | None = None, organization: str | None = None
) -> None:
    logger.info("Scheduling boefjes")
    count = 0
    for ooi, config in get_expired_boefjes(boefje_id, input_oois, organization):
        task_id = uuid.uuid4()
        task = Task.objects.create(
            id=task_id,
            type="boefje",
            organization=config.organization,
            status=TaskStatus.QUEUED,
            data=BoefjeMeta(
                id=task_id,
                boefje=Boefje(
                    id=config.boefje.id,
                    plugin_id=config.boefje.plugin_id,
                    name=config.boefje.name,
                    version=config.boefje.version,
                    oci_image=config.boefje.oci_image,
                    oci_arguments=config.boefje.oci_arguments,
                ),
                input_ooi=ooi.primary_key,
                input_ooi_data=ooi.serialize(),
                organization=config.organization.code,
            ).model_dump(mode="json"),
        )
        scheduler_client(config.organization).push_task(task)
        count += 1

    logger.info("Finished scheduling %s boefjes", count)


@app.task(bind=True)
def report(self, organization: str, report_recipe_id: str) -> None:
    logger.info("Creating report [org=%s]", organization)

    runner = LocalReportRunner(datetime.now(timezone.utc))
    report_task = ReportTask(organisation_id=organization, report_recipe_id=str(report_recipe_id))

    try:
        runner.run(report_task)
    except:
        Task.objects.filter(id=self.request.id).update(status=TaskStatus.FAILED)
        raise
    else:
        Task.objects.filter(id=self.request.id).update(status=TaskStatus.COMPLETED)


@app.task(bind=True)
def boefje(self, organization: str, plugin_id: str, input_ooi: str) -> None:
    logger.info("Starting task %s for boefje [org=%s, plugin_id=%s]", self.request.id, organization, plugin_id)

    local_repository = get_local_repository()
    storage = SimpleBoefjeStorageInterface()
    handler = LocalBoefjeHandler(local_repository, storage)
    config = BoefjeConfig.objects.get(boefje__plugin_id=plugin_id, organization__code=organization)

    if not config.enabled:
        raise RuntimeError("Boefje not enabled")

    scheduler_task = Task.objects.get(id=self.request.id)
    scheduler_task.status = TaskStatus.RUNNING
    scheduler_task.save()

    try:
        raw_file_ids, boefje_output = handler.handle(WorkerTask.from_db(scheduler_task))
    except:
        scheduler_task.status = TaskStatus.FAILED
        scheduler_task.save()
        raise
    else:
        scheduler_task.status = TaskStatus.COMPLETED
        scheduler_task.save()

    logger.info("dispatching %s raw files", len(boefje_output.files))

    for file in boefje_output.files:
        raw_file_id = raw_file_ids[file.name]
        app.send_task("openkat.tasks.process_raw", (raw_file_id,))

    gc.collect()
    logger.info("Handled boefje [org=%s, plugin_id=%s]", organization, plugin_id)


@app.task(bind=True)
def docker_boefje(self, organization: str, plugin_id: str, input_ooi: str) -> None:
    logger.info(
        "Starting task %s for ontainerized boefje [org=%s, plugin_id=%s]", self.request.id, organization, plugin_id
    )

    handler = DockerBoefjeHandler()
    config = BoefjeConfig.objects.get(boefje__plugin_id=plugin_id, organization__code=organization)

    if not config.enabled:
        raise RuntimeError("Containerized Boefje not enabled")

    scheduler_task = Task.objects.get(id=self.request.id)
    scheduler_task.status = TaskStatus.RUNNING
    scheduler_task.save()

    try:
        handler.handle(scheduler_task)
    except:
        Task.objects.filter(id=self.request.id).update(status=TaskStatus.FAILED)
        raise

    logger.info("dispatching raw files")

    for file in File.objects.filter(task_result__task_id=self.request.id):
        app.send_task("openkat.tasks.process_raw", (str(file.id),))

    logger.info("Handled containerized boefje [org=%s, plugin_id=%s]", organization, plugin_id)


@app.task
def process_raw(raw_file_id: int, handle_error: bool = False) -> None:
    logger.info("Handling raw file %s", raw_file_id)
    file = File.objects.get(id=raw_file_id)

    if file.type == "error/boefje" and not handle_error:
        logger.info("Raw file %s contains an exception trace and handle_error is set to False. Skipping.", raw_file_id)
        return

    scheduler = scheduler_client(file.task_result.task.organization)
    local_repository = get_local_repository()

    for normalizer_resource in local_repository.resolve_normalizers().values():
        if file.type not in normalizer_resource.normalizer.consumes:
            continue

        config = NormalizerConfig.objects.filter(
            normalizer__plugin_id=normalizer_resource.normalizer.plugin_id,
            organization=file.task_result.task.organization,
        ).first()

        if not config:
            normalizer_db = NormalizerDB.objects.get(plugin_id=normalizer_resource.normalizer.plugin_id)
        else:
            if not config.enabled:
                continue

            normalizer_db = config.normalizer

        task_id = uuid.uuid4()
        task = Task.objects.create(
            id=task_id,
            type="normalizer",
            organization=file.task_result.task.organization,
            data=NormalizerMeta(
                id=task_id,
                normalizer=Normalizer(
                    id=normalizer_db.id,
                    name=normalizer_db.name,
                    plugin_id=normalizer_db.plugin_id,
                    version=normalizer_db.version,
                ),
                raw_data=RawData(
                    id=raw_file_id, boefje_meta=BoefjeMeta.model_validate(file.task_result.task.data), type=file.type
                ),
            ).model_dump(mode="json"),
        )
        scheduler.push_task(task)


@app.task(bind=True)
def normalizer(self, organization: str, plugin_id: str, raw_file_id: str | uuid.UUID) -> None:
    logger.info("Starting normalizer [org=%s, plugin_id=%s, raw_file_id=%s]", organization, plugin_id, raw_file_id)

    local_repository = get_local_repository()
    connector = settings.OCTOPOES_FACTORY(organization)

    handler = LocalNormalizerHandler(local_repository, connector)
    config = NormalizerConfig.objects.filter(normalizer__plugin_id=plugin_id, organization__code=organization).first()
    scheduler_task = Task.objects.get(id=self.request.id)

    if config and not config.enabled:
        raise RuntimeError("Normalizer not enabled")

    try:
        handler.handle(scheduler_task)
    except:
        Task.objects.filter(id=self.request.id).update(status=TaskStatus.FAILED)
        raise
    else:
        Task.objects.filter(id=self.request.id).update(status=TaskStatus.COMPLETED)

    logger.info("Handled normalizer [org=%s, plugin_id=%s]", organization, plugin_id)

    app.send_task(
        "openkat.tasks.recalculate_scan_profiles",
        (organization,),
        queue=settings.QUEUE_NAME_OCTOPOES,
        task_id=str(uuid.uuid4()),
    )
