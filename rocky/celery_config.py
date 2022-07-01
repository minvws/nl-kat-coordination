# Celery

from os import getenv

QUEUE_URI = getenv("QUEUE_URI")

broker_url = QUEUE_URI
result_backend = f"rpc://{QUEUE_URI}"

task_serializer = "json"
result_serializer = "json"
event_serializer = "json"
accept_content = ["application/json", "application/x-python-serialize"]
result_accept_content = ["application/json", "application/x-python-serialize"]
