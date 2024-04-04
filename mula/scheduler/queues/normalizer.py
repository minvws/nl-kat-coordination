import mmh3

from scheduler import models
from scheduler.utils import dict_utils

from .pq import PriorityQueue


class NormalizerPriorityQueue(PriorityQueue):
    def create_hash(self, p_item: models.PrioritizedItem) -> str:
        """Create a hash for the given item. This hash is used to determine if
        the item is already in the queue.

        Args:
            p_item: A PrioritizedItem model.

        Returns:
            A string representing the hash.
        """
        normalizer_id = dict_utils.deep_get(
            p_item.model_dump(),
            ["data", "normalizer", "id"],
        )

        boefje_meta_id = dict_utils.deep_get(
            p_item.model_dump(),
            ["data", "raw_data", "boefje_meta", "id"],
        )

        organization = dict_utils.deep_get(
            p_item.model_dump(),
            ["data", "raw_data", "boefje_meta", "organization"],
        )

        return mmh3.hash_bytes(f"{normalizer_id}-{boefje_meta_id}-{organization}").hex()
