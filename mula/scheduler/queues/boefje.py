import mmh3

from scheduler import models
from scheduler.utils import dict_utils

from .pq import PriorityQueue


class BoefjePriorityQueue(PriorityQueue):
    def create_hash(self, task: models.Task) -> str:
        """Create a hash for the given item. This hash is used to determine if
        the item is already in the queue.

        Args:
            task: A PrioritizedItem model.

        Returns:
            A string representing the hash.
        """
        boefje_id = dict_utils.deep_get(task.model_dump(), ["data", "boefje", "id"])
        input_ooi = dict_utils.deep_get(task.model_dump(), ["data", "input_ooi"])
        organization = dict_utils.deep_get(task.model_dump(), ["data", "organization"])

        if input_ooi:
            return mmh3.hash_bytes(f"{input_ooi}-{boefje_id}-{organization}").hex()

        return mmh3.hash_bytes(f"{boefje_id}-{organization}").hex()
