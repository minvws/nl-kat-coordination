import time

from scheduler.connectors import listeners


class MockListener(listeners.Listener):
    def listen(self) -> None:
        time.sleep(1)

    def stop(self) -> None:
        pass
