import json
import logging.config
from pathlib import Path
from types import SimpleNamespace

from prometheus_client import CollectorRegistry, Gauge, Info

import scheduler
from scheduler.config import settings
from scheduler.connectors import services
from scheduler.repositories import sqlalchemy, stores


class AppContext:
    """AppContext allows shared data between modules.

    Attributes:
        config:
            A settings.Settings object containing configurable application
            settings
        services:
            A dict containing all the external services connectors that
            are used and need to be shared in the scheduler application.
        datastore:
            A SQLAlchemy.SQLAlchemy object used for storing and retrieving
            tasks.
    """

    def __init__(self) -> None:
        """Initializer of the AppContext class."""
        self.config: settings.Settings = settings.Settings()

        # Load logging configuration
        with Path(self.config.log_cfg).open("rt", encoding="utf-8") as f:
            logging.config.dictConfig(json.load(f))

        # Services
        katalogus_service = services.Katalogus(
            host=self.config.host_katalogus,
            source=f"scheduler/{scheduler.__version__}",
            cache_ttl=self.config.katalogus_cache_ttl,
        )

        bytes_service = services.Bytes(
            host=self.config.host_bytes,
            user=self.config.host_bytes_user,
            password=self.config.host_bytes_password,
            source=f"scheduler/{scheduler.__version__}",
        )

        octopoes_service = services.Octopoes(
            host=self.config.host_octopoes,
            source=f"scheduler/{scheduler.__version__}",
            orgs=katalogus_service.get_organisations(),
            timeout=self.config.octopoes_request_timeout,
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

        # Repositories
        if not self.config.db_uri.startswith("postgresql"):
            raise Exception("PostgreSQL is the only supported database backend")

        datastore = sqlalchemy.SQLAlchemy(self.config.db_uri)
        self.task_store: stores.TaskStorer = sqlalchemy.TaskStore(datastore)
        self.pq_store: stores.PriorityQueueStorer = sqlalchemy.PriorityQueueStore(datastore)

        # Metrics collector registry
        self.metrics_registry: CollectorRegistry = CollectorRegistry()

        Info(
            name="app_settings",
            documentation="Scheduler configuration settings",
            registry=self.metrics_registry,
        ).info(
            {
                "pq_maxsize": str(self.config.pq_maxsize),
                "pq_populate_interval": str(self.config.pq_populate_interval),
                "pq_populate_grace_period": str(self.config.pq_populate_grace_period),
                "pq_populate_max_random_objects": str(self.config.pq_populate_max_random_objects),
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
