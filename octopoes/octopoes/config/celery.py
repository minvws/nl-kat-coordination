from kombu import Queue

from octopoes.config.settings import Settings

settings = Settings()

broker_url = settings.queue_uri
result_backend = f"rpc://{settings.queue_uri}"

task_serializer = "json"
result_serializer = "json"
event_serializer = "json"
accept_content = ["application/json", "application/x-python-serialize"]
result_accept_content = ["application/json", "application/x-python-serialize"]

task_queues = (Queue(settings.queue_name_octopoes),)
