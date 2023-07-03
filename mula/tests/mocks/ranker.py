from typing import Any

from scheduler import rankers


class MockRanker(rankers.Ranker):
    def rank(self, obj: Any) -> int:
        return 0
