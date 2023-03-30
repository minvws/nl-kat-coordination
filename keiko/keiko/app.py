"""Keiko's API entrypoint."""

from keiko.api import construct_api
from keiko.logging import setup_loggers
from keiko.settings import Settings

settings = Settings()

# Load logging configuration
setup_loggers(settings)

api = construct_api(settings)
