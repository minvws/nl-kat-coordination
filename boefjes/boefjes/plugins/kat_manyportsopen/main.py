import json
from typing import List, Tuple, Union

from boefjes.job_models import BoefjeMeta


# Until we have an implementation of bits, all logic will happen in normalizer
def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    results = {}

    return [(set(), json.dumps(results))]
