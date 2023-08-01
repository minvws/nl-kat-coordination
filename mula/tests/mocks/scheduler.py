import time

from scheduler import schedulers

from . import listener


class MockScheduler(schedulers.Scheduler):
    def run(self) -> None:
        # Listener
        self.listeners["mock-listener"] = listener.MockListener()
        self.run_in_thread(
            name="mock-listener",
            target=self.listeners["mock-listener"].listen,
            loop=True,
        )

        # Thread
        self.run_in_thread(
            name="mock-scheduler",
            target=self._run,
            loop=True,
        )

    def _run(self) -> None:
        time.sleep(1)
