import os

from celery import Celery
from celery.signals import setup_logging
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


app.conf.beat_schedule = {
    "schedule-scan-profile-recalculations": {
        "task": "openkat.tasks.schedule_scan_profile_recalculations",
        "schedule": settings.SCAN_LEVEL_RECALCULATION_INTERVAL,
        "args": tuple(),
    },
    "schedule-boefjes": {"task": "openkat.tasks.schedule", "schedule": settings.SCHEDULE_INTERVAL, "args": tuple()},
    "queue": settings.QUEUE_NAME_SCHEDULE,
    "reschedule-boefjes": {"task": "openkat.tasks.reschedule", "schedule": settings.SCHEDULE_INTERVAL, "args": tuple()},
}
