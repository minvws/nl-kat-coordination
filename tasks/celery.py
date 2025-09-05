import os

from celery import Celery
from celery.signals import setup_logging, worker_shutdown
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openkat.settings")
app = Celery()
app.config_from_object(settings.CELERY)
app.autodiscover_tasks()


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig  # noqa
    from django.conf import settings  # noqa

    dictConfig(settings.LOGGING)


@worker_shutdown.connect
def cancel_all_tasks(*args, **kwargs):
    from tasks.models import Task, TaskStatus

    for task in Task.objects.filter(
        status__in=[TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.DISPATCHED]
    ):
        task.cancel()


app.conf.beat_schedule = {
    "schedule-scan-profile-recalculations": {
        "task": "tasks.tasks.schedule_scan_profile_recalculations",
        "schedule": settings.SCAN_LEVEL_RECALCULATION_INTERVAL,
        "args": tuple(),
        "options": {"queue": settings.QUEUE_NAME_SCHEDULE},
    },
    "schedule-boefjes": {
        "task": "tasks.tasks.schedule",
        "schedule": settings.SCHEDULE_INTERVAL,
        "args": tuple(),
        "options": {"queue": settings.QUEUE_NAME_SCHEDULE},
    },
    "reschedule-boefjes": {
        "task": "tasks.tasks.reschedule",
        "schedule": settings.SCHEDULE_INTERVAL,
        "args": tuple(),
        "options": {"queue": settings.QUEUE_NAME_SCHEDULE},
    },
    "reschedule": {
        "task": "tasks.new_tasks.reschedule",
        "schedule": settings.SCHEDULE_INTERVAL // 6,
        "args": tuple(),
        "options": {"queue": settings.QUEUE_NAME_SCHEDULE},
    },
}
