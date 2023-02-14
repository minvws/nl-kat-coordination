import mmh3
from scheduler import models
from scheduler.utils import dict_utils

from .pq import PriorityQueue


class BoefjePriorityQueue(PriorityQueue):
    def create_hash(self, p_item: models.PrioritizedItem) -> str:
        boefje_id = dict_utils.deep_get(p_item.dict(), ["data", "boefje", "id"])
        input_ooi = dict_utils.deep_get(p_item.dict(), ["data", "input_ooi"])
        organization = dict_utils.deep_get(p_item.dict(), ["data", "organization"])

        return mmh3.hash_bytes(f"{input_ooi}-{boefje_id}-{organization}").hex()
