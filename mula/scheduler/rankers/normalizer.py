from scheduler import models

from .ranker import Ranker


class NormalizerRanker(Ranker):
    def rank(self, task: models.Task) -> int:
        """Ranking of normalizer tasks, we want raw files that have been
        created a long time ago to be processed earlier."""
        return int(task.raw_data.boefje_meta.ended_at.timestamp())
