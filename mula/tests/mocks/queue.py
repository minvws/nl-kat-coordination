from scheduler import models, queues
from scheduler.utils import dict_utils


class MockPriorityQueue(queues.PriorityQueue):
    def create_hash(self, p_item: models.PrioritizedItem) -> str:
        return dict_utils.deep_get(p_item.model_dump(), ["data", "id"])
