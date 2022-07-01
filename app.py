from celery import Celery

import celery_config

app = Celery()
app.config_from_object(celery_config)
