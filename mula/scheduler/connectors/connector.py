import logging
import socket
import time
from typing import Callable

import requests


class Connector:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def is_host_available(self, hostname: str, port: int) -> bool:
        """Check if the host is available.

        Returns:
            A boolean
        """
        try:
            socket.create_connection((hostname, port))
            return True
        except socket.error:
            return False

    def is_host_healthy(self, host: str, health_endpoint: str) -> bool:
        """Check if host is healthy by inspecting the host's health endpoint.

        Returns:
            A boolean
        """
        try:
            response = requests.get(f"{host}{health_endpoint}", timeout=5)
            healthy = response.json().get("healthy")
            return healthy
        except requests.exceptions.RequestException as exc:
            self.logger.warning("Exception: %s", exc)
            return False

    def retry(self, func: Callable, *args, **kwargs) -> bool:
        """Retry a function until it returns True.

        Args:
            func: A python callable that needs to be retried.

        Returns:
            A boolean signifying whether or not the func was executed successfully.
        """
        for i in range(10):
            if func(*args, **kwargs):
                self.logger.info(
                    "Function %s, executed successfully. Retry count: %d [name=%s, args=%s, kwargs=%s]",
                    func.__name__,
                    i,
                    func.__name__,
                    args,
                    kwargs,
                )
                return True

            self.logger.warning(
                "Function %s, failed. Retry count: %d [name=%s, args=%s, kwargs=%s]",
                func.__name__,
                i,
                func.__name__,
                args,
                kwargs,
            )

            time.sleep(10)

        return False
