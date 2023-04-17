import mmh3

from scheduler import models
from scheduler.utils import dict_utils

from .pq import PriorityQueue


class NormalizerPriorityQueue(PriorityQueue):
    def create_hash(self, p_item: models.PrioritizedItem) -> str:
        normalizer_id = dict_utils.deep_get(p_item.dict(), ["data", "normalizer", "id"])
        boefje_meta_id = dict_utils.deep_get(p_item.dict(), ["data", "raw_data", "boefje_meta", "id"])
        organization = dict_utils.deep_get(p_item.dict(), ["data", "raw_data", "boefje_meta", "organization"])

        return mmh3.hash_bytes(f"{normalizer_id}-{boefje_meta_id}-{organization}").hex()
