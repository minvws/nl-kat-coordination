import logging
import os
import threading

from .datastore import GUID
from .dict_utils import ExpiredError, ExpiringDict, deep_get
from .thread import ThreadRunner

logger = logging.getLogger(__name__)


def shutdown(args) -> None:
    """Gracefully shutdown the scheduler application, and all threads."""
    logger.info("Shutting down...")

    for t in threading.enumerate():
        if t is threading.current_thread():
            continue

        if t is threading.main_thread():
            continue

        if not t.is_alive():
            continue

        t.join(5)

    logger.info("Shutdown complete")

    # We're calling this here, because we want to issue a shutdown from
    # within a thread, otherwise it will not exit a docker container.
    # Source: https://stackoverflow.com/a/1489838/1346257
    os._exit(1)


# When a unhanded exception occurs, we want to shutdown the application
threading.excepthook = shutdown
