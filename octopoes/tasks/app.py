from celery import Celery

import octopoes.config.celery as celery_config

app = Celery()
app.config_from_object(celery_config)
