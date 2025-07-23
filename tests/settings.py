from unittest.mock import patch

import structlog

from openkat.settings import *  # noqa: F401, F403, TID251

STORAGES = {
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
}
COMPRESS_OFFLINE = False

# Disable caching of loggers so they can be changed in tests.
structlog.configure(cache_logger_on_first_use=False)


def OCTOPOES_FACTORY(organization: str):  # type: ignore
    from octopoes.config.settings import Settings
    from octopoes.connector.octopoes import OctopoesAPIConnector

    with patch("octopoes.core.app.EventManager") as manager:
        manager().client = organization
        return OctopoesAPIConnector(organization, Settings())
