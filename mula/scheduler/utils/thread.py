import logging
import threading
from typing import Any, Callable, Optional


class ThreadRunner(threading.Thread):
    """ThreadRunner extends threading.Thread to allow for graceful shutdown
    using event signalling. Additionally to the standard threading.Thread
    attributes we use the following attributes.

    Attributes:
        logger:
            The logger for the class.
        stop_event:
            A threading.Event object used for signalling thread stop events.
        interval:
            A float describing the time between loop iterations.
        exception:
            A python Exception that can be set in order to signify that
            an exception has occurred during the execution of the thread.
    """

    def __init__(
        self,
        name: str,
        target: Callable[[], Any],
        stop_event: threading.Event,
        interval: float = 0.01,
        daemon: bool = False,
    ) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.stop_event: threading.Event = stop_event
        self.interval: float = interval
        self.exception: Optional[Exception] = None
        self._target: Callable[[], Any] = target

        super().__init__(target=self._target, daemon=daemon)

        self.name = f"{self.name}-{name}" if name else self.name

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                self._target()
                self.stop_event.wait(self.interval)
            except Exception as e:
                self.exception = e
                self.logger.exception(e)
                self.stop()

        self.logger.warning("Thread stopped: %s", self.name)

    def join(self, timeout: Optional[float] = None) -> None:
        self.logger.warning("Stopping thread: %s", self.name)

        self.stop_event.set()
        super().join(timeout)

        self.logger.warning("Thread stopped: %s", self.name)

    def stop(self) -> None:
        self.stop_event.set()
