import random
from datetime import datetime, timedelta, timezone
from typing import Any

from scheduler.utils import cron

from .ranker import Ranker


class DefaultDeadlineRanker(Ranker):
    def rank(self, obj: Any) -> int:
        """Create a deadline for a job

        Args:
            obj (Any): The object to rank

        Returns:
            int: The timestamp of the deadline
        """
        # Do we have a cron expression?
        if obj is not None and obj.cron_expression:
            try:
                next_run = cron.next_run(obj.cron_expression)
            except Exception as exc:
                raise ValueError(f"Invalid cron expression: {obj.cron_expression}") from exc
            return int(next_run.timestamp())

        # We at least delay a job by the grace period
        minimum = self.ctx.config.pq_grace_period
        deadline = datetime.now(timezone.utc) + timedelta(seconds=minimum)

        # We want to delay the job by a random amount of time, in a range of 5 hours
        jitter_range_seconds = 5 * 60 * 60
        jitter_offset = timedelta(seconds=random.uniform(-jitter_range_seconds, jitter_range_seconds))

        # Check if the adjusted time is earlier than the minimum, and
        # ensure that the adjusted time is not earlier than the deadline
        adjusted_time = deadline + jitter_offset
        adjusted_time = max(adjusted_time, deadline)

        return int((datetime.now(timezone.utc) + timedelta(seconds=minimum)).timestamp())
