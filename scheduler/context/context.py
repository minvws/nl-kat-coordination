import json
import logging.config
import threading
from types import SimpleNamespace

import scheduler
from scheduler.config import settings
from scheduler.connectors import listeners, services
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
        stop_event: A threading.Event object used for communicating a stop
            event across threads.
        datastore:
            A SQLAlchemy.SQLAlchemy object used for storing and retrieving
            tasks.
    """

    def __init__(self) -> None:
        """Initializer of the AppContext class."""
        self.config: settings.Settings = settings.Settings()

        # Load logging configuration
        with open(self.config.log_cfg, "rt", encoding="utf-8") as f:
            logging.config.dictConfig(json.load(f))

        # Services
        katalogus = services.Katalogus(
            host=self.config.host_katalogus,
            source=f"scheduler/{scheduler.__version__}",
        )

        bytes = services.Bytes(
            host=self.config.host_bytes,
            user=self.config.host_bytes_user,
            password=self.config.host_bytes_password,
            source=f"scheduler/{scheduler.__version__}",
        )

        octopoes = services.Octopoes(
            host=self.config.host_octopoes,
            source=f"scheduler/{scheduler.__version__}",
            orgs=katalogus.get_organisations(),
        )

        # Listeners
        mutations = listeners.ScanProfileMutation(
            dsn=self.config.host_mutation,
        )

        raw_data = listeners.RawData(
            dsn=self.config.host_raw_data,
        )

        normalizer_meta = listeners.NormalizerMeta(
            dsn=self.config.host_normalizer_meta,
        )

        # Register external services, SimpleNamespace allows us to use dot
        # notation
        self.services: SimpleNamespace = SimpleNamespace(
            **{
                services.Katalogus.name: katalogus,
                services.Octopoes.name: octopoes,
                services.Bytes.name: bytes,
                listeners.ScanProfileMutation.name: mutations,
                listeners.RawData.name: raw_data,
                listeners.NormalizerMeta.name: normalizer_meta,
            }
        )

        self.stop_event: threading.Event = threading.Event()

        # Repositories
        datastore = sqlalchemy.SQLAlchemy(self.config.database_dsn)
        self.task_store: stores.TaskStorer = sqlalchemy.TaskStore(datastore)
        self.pq_store: stores.PriorityQueueStorer = sqlalchemy.PriorityQueueStore(datastore)
