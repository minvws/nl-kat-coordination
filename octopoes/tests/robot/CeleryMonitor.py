import threading
from collections import Counter
from operator import itemgetter

from celery import Celery
from robot.api import logger

apps = {}


def get_app(queue_uri: str) -> Celery:
    config = {
        "broker_url": queue_uri,
        "broker_pool_limit": 0,
        "worker_concurrency": 1,
        "worker_prefetch_multiplier": 0,
        "result_backend": f"rpc://{queue_uri}",
        "task_serializer": "json",
        "result_serializer": "json",
        "event_serializer": "json",
        "accept_content": ["application/json", "application/x-python-serialize"],
        "result_accept_content": ["application/json", "application/x-python-serialize"],
        "task_queues": ("octopoes",),
        "task_alway_eager": True,
    }
    if queue_uri not in apps:
        apps[queue_uri] = Celery()
        apps[queue_uri].config_from_object(config)
    return apps[queue_uri]


class Monitor:
    def __init__(self, queue_uri: str):
        self._app = get_app(queue_uri)
        self._thread = threading.Thread(target=self._monitor_events, args=(self._app,), daemon=True)
        self._tasks = {}
        self._receiver = None
        self._started = threading.Event()

    @property
    def tasks(self):
        return self._tasks

    def start(self):
        self._thread.start()

    def stop(self):
        self._started.wait()
        self._receiver.should_stop = True

    def _on_event(self, event):
        self._tasks[event["uuid"]] = event

    def _monitor_events(self, celery_app: Celery) -> None:
        logger.info("Monitoring events")
        with celery_app.connection(connect_timeout=2) as connection:
            logger.info(f"Connection made: {connection.connected}")

            self._receiver = celery_app.events.Receiver(
                connection,
                handlers={
                    "task-sent": self._on_event,
                    "task-received": self._on_event,
                    "task-started": self._on_event,
                    "task-succeeded": self._on_event,
                    "task-failed": self._on_event,
                    "task-rejected": self._on_event,
                    "task-revoked": self._on_event,
                    "task-retired": self._on_event,
                },
            )
            self._started.set()
            self._receiver.capture(limit=None, timeout=None, wakeup=True)

    def sum_per_type(self) -> Counter:
        return Counter(map(itemgetter("type"), self.tasks.values()))


class CeleryMonitor:
    ROBOT_LIBRARY_SCOPE = "TEST"

    def __init__(self):
        self._monitor: Monitor = None

    def start_monitoring(self, queue_uri: str):
        self._monitor = Monitor(queue_uri)
        self._monitor.start()
        logger.info("Started monitoring")

    def stop_monitoring(self):
        self._monitor.stop()

    def count_tasks(self, event_type: str) -> int:
        event_type = "task-" + event_type.lower()

        sum_per_type = self._monitor.sum_per_type()
        logger.info(f"Sum tasks per type: {sum_per_type}")

        if event_type not in sum_per_type:
            return 0
        return self._monitor.sum_per_type()[event_type]

    def remove_tasks(self, event_type: str) -> int:
        event_type = "task-" + event_type.lower()

        tasks = list(filter(lambda v: v["type"] == event_type, self._monitor.tasks.values()))
        for task in tasks:
            del self._monitor.tasks[task]

        return len(tasks)
