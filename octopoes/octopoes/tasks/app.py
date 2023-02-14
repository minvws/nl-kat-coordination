from celery import Celery

import octopoes.config.celery as celery_config
from octopoes.config.settings import Settings

settings = Settings()

app = Celery()
app.config_from_object(celery_config)

app.conf.beat_schedule = {
    "schedule-scan-profile-recalculations": {
        "task": "octopoes.tasks.tasks.schedule_scan_profile_recalculations",
        "schedule": settings.scan_level_recalculation_interval,
        "args": tuple(),
    },
}
