from kombu import Queue

from config import settings

broker_url = settings.queue_uri
result_backend = f"rpc://{settings.queue_uri}"

task_serializer = "json"
result_serializer = "json"
event_serializer = "json"
accept_content = ["application/json", "application/x-python-serialize"]
result_accept_content = ["application/json", "application/x-python-serialize"]

task_queues = (
    Queue(settings.queue_name_boefjes),
    Queue(settings.queue_name_normalizers),
)

worker_concurrency = settings.worker_concurrency
