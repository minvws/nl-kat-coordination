"""Application Context module."""

import logging.config
import threading
from types import SimpleNamespace

import yaml

from octopoes.config import settings
from octopoes.connectors.services.katalogus import Katalogus
from octopoes.version import version


def get_katalogus(uri: str) -> Katalogus:
    """Katalogus client factory."""
    return Katalogus(
        host=uri,
        source=f"octopoes/{version}",
    )


class AppContext:
    """AppContext allows shared data between modules.

    Attributes:
        config:
            A settings.Settings object containing configurable application
            settings
        services:
            A dict containing all the external services connectors that
            are used and need to be shared in the octopoes application.
        stop_event: A threading.Event object used for communicating a stop
            event across threads.
    """

    def __init__(self) -> None:
        """Initialize instance."""
        self.config: settings.Settings = settings.Settings()

        self.logger = logging.getLogger(__name__)

        # Load logging configuration
        try:
            with open(self.config.log_cfg, "r") as log_config:
                logging.config.dictConfig(yaml.safe_load(log_config))
                self.logger.info("Configured loggers with config: %s", self.config.log_cfg)
        except FileNotFoundError:
            self.logger.warning("No log config found at: %s", self.config.log_cfg)

        self.katalogus_svc = get_katalogus(self.config.katalogus_uri)

        # Register external services, SimpleNamespace allows us to use dot
        # notation
        self.services: SimpleNamespace = SimpleNamespace(
            **{
                Katalogus.name: self.katalogus_svc,
            }
        )

        self.stop_event: threading.Event = threading.Event()
