import time

from .dispatcher import CeleryDispatcher


class BoefjeDispatcher(CeleryDispatcher):
    pass


class BoefjeDispatcherTimeBased(CeleryDispatcher):
    """A time-based BoefjeDispatcher allows for executing jobs at a certain
    time. The threshold of dispatching jobs is the current time, and based
    on the time-based priority score of the jobs on the queue. The dispatcher
    determines to dispatch the job.
    """

    def get_threshold(self) -> int:
        return int(time.time())
