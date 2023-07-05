import time

from scheduler import schedulers


class MockScheduler(schedulers.Scheduler):
    def run(self) -> None:
        self.run_in_thread(
            name="mock-scheduler",
            target=self._run,
            loop=True,
        )

    def _run(self) -> None:
        time.sleep(1)
