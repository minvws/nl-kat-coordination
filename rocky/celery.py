import logging
from threading import Thread

from celery import Celery

from rocky.signals import task_received, task_succeeded, task_failed

app = Celery()

app.config_from_object("rocky.celery_config")

logging.getLogger("amqp.connection.Connection.heartbeat_tick").setLevel(logging.INFO)
logger = logging.getLogger(__name__)


# trigger signals on task events
def _on_event(event) -> None:
    if event["type"] == "task-received":
        logger.info("Got task received event")
        task_received.send(event)
    elif event["type"] == "task-succeeded":
        logger.info("Got task succeeded event")
        task_succeeded.send(event)
    elif event["type"] == "task-failed":
        logger.info("Got task failed event")
        task_failed.send(event)


# create an event receiver to monitor task events
def monitor_events(celery_app: Celery) -> None:
    with celery_app.connection() as connection:
        recv = celery_app.events.Receiver(
            connection,
            handlers={
                "task-received": _on_event,
                "task-succeeded": _on_event,
                "task-failed": _on_event,
            },
        )
        recv.capture(limit=None, timeout=None, wakeup=True)


def start_tasks_monitoring():
    # start monitoring task events in the background
    Thread(target=monitor_events, args=(app,), daemon=True).start()
