import json
import logging.config
from pathlib import Path
from types import SimpleNamespace

from prometheus_client import CollectorRegistry, Gauge, Info

import scheduler
from scheduler import storage
from scheduler.config import settings
from scheduler.connectors import services
from scheduler.utils import remove_trailing_slash


class AppContext:
    """AppContext allows shared data between modules.

    Attributes:
        config:
            A settings.Settings object containing configurable application
            settings
        services:
            A dict containing all the external services connectors that
            are used and need to be shared in the scheduler application.
        task_store:
            A stores.TaskStore object used for storing tasks.
        pq_store:
            A stores.PriorityQueueStore object used for storing priority queues.
        metrics_registry:
            A prometheus_client.CollectorRegistry object used for storing metrics.
        metrics_qsize:
            A prometheus_client.Gauge object used for storing the queue size of
            the schedulers.
    """

    def __init__(self) -> None:
        """Initializer of the AppContext class."""
        self.config: settings.Settings = settings.Settings()

        # Load logging configuration
        with Path(self.config.log_cfg).open("rt", encoding="utf-8") as f:
            logging.config.dictConfig(json.load(f))

        # Services
        katalogus_service = services.Katalogus(
            host=remove_trailing_slash(str(self.config.host_katalogus)),
            source=f"scheduler/{scheduler.__version__}",
            timeout=self.config.katalogus_request_timeout,
            pool_connections=self.config.katalogus_pool_connections,
            cache_ttl=self.config.katalogus_cache_ttl,
        )

        bytes_service = services.Bytes(
            host=remove_trailing_slash(str(self.config.host_bytes)),
            source=f"scheduler/{scheduler.__version__}",
            user=self.config.host_bytes_user,
            password=self.config.host_bytes_password,
            timeout=self.config.bytes_request_timeout,
            pool_connections=self.config.bytes_pool_connections,
        )

        octopoes_service = services.Octopoes(
            host=remove_trailing_slash(str(self.config.host_octopoes)),
            source=f"scheduler/{scheduler.__version__}",
            timeout=self.config.octopoes_request_timeout,
            pool_connections=self.config.octopoes_pool_connections,
            orgs=katalogus_service.get_organisations(),
        )

        # Register external services, SimpleNamespace allows us to use dot
        # notation
        self.services: SimpleNamespace = SimpleNamespace(
            **{
                services.Katalogus.name: katalogus_service,
                services.Octopoes.name: octopoes_service,
                services.Bytes.name: bytes_service,
            }
        )

        # Datastores, SimpleNamespace allows us to use dot notation
        dbconn = storage.DBConn(str(self.config.db_uri))
        self.datastores: SimpleNamespace = SimpleNamespace(
            **{
                storage.TaskStore.name: storage.TaskStore(dbconn),
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(dbconn),
            }
        )

        # Metrics collector registry
        self.metrics_registry: CollectorRegistry = CollectorRegistry()

        Info(
            name="app_settings",
            documentation="Scheduler configuration settings",
            registry=self.metrics_registry,
        ).info(
            {
                "pq_maxsize": str(self.config.pq_maxsize),
                "pq_grace_period": str(self.config.pq_grace_period),
                "pq_max_random_objects": str(self.config.pq_max_random_objects),
                "katalogus_cache_ttl": str(self.config.katalogus_cache_ttl),
                "monitor_organisations_interval": str(self.config.monitor_organisations_interval),
            }
        )

        self.metrics_qsize = Gauge(
            name="scheduler_qsize",
            documentation="Size of the scheduler queue",
            registry=self.metrics_registry,
            labelnames=["scheduler_id"],
        )

        self.metrics_task_status_counts = Gauge(
            name="scheduler_task_status_counts",
            documentation="Number of tasks in each status",
            registry=self.metrics_registry,
            labelnames=["scheduler_id", "status"],
        )
