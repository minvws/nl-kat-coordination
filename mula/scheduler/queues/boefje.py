import mmh3

from scheduler import models
from scheduler.utils import dict_utils

from .pq import PriorityQueue


class BoefjePriorityQueue(PriorityQueue):
    def create_hash(self, schema: models.TaskSchema) -> str:
        """Create a hash for the given item. This hash is used to determine if
        the item is already in the queue.

        Args:
            p_item: A PrioritizedItem model.

        Returns:
            A string representing the hash.
        """
        boefje_id = dict_utils.deep_get(schema.model_dump(), ["data", "boefje", "id"])
        input_ooi = dict_utils.deep_get(schema.model_dump(), ["data", "input_ooi"])
        organization = dict_utils.deep_get(schema.model_dump(), ["data", "organization"])

        if input_ooi:
            return mmh3.hash_bytes(f"{input_ooi}-{boefje_id}-{organization}").hex()

        return mmh3.hash_bytes(f"{boefje_id}-{organization}").hex()
