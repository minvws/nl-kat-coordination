from datetime import datetime, timedelta, timezone
from typing import Any

from .ranker import Ranker


class JobDeadlineRanker(Ranker):
    def rank(self, obj: Any) -> int:
        # TODO: make more sophisticated calculation
        return int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp())
