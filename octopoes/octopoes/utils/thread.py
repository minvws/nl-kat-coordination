"""Threading logic."""

import logging
import threading
from typing import Any, Callable, Optional


class ThreadRunner(threading.Thread):
    """
    ThreadRunner extends threading.Thread to allow for graceful shutdown using event signalling.

    Additionally, to the standard threading.Thread attributes we use the following attributes.

    Attributes
    ----------
        logger:
            The logger for the class.
        stop_event:
            A threading.Event object used for signalling thread stop events.
        interval:
            A float describing the time between loop iterations.
        exception:
            A python Exception that can be set in order to signify that
            an exception has occured during the execution of the thread.

    """

    def __init__(
        self,
        target: Callable[[], Any],
        stop_event: threading.Event,
        interval: float = 0.01,
        daemon: bool = False,
    ) -> None:
        """Initialize the ThreadRunner class."""
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.stop_event: threading.Event = stop_event
        self.interval: float = interval
        self.exception: Optional[Exception] = None
        self._target: Callable[[], Any] = target

        super().__init__(target=self._target, daemon=daemon)

    def run(self) -> None:
        """Run the thread."""
        while not self.stop_event.is_set():
            try:
                self._target()
            except Exception as exc:  # pylint: disable=broad-except
                self.exception = exc
                self.logger.exception(exc)
                self.stop()

            self.stop_event.wait(self.interval)

    def join(self, timeout: Optional[float] = None) -> None:
        """Join the thread."""
        self.logger.debug("Stopping thread")

        self.stop_event.set()
        super().join(timeout)

        self.logger.debug("Thread stopped")

    def stop(self) -> None:
        """Stop the thread."""
        self.stop_event.set()
