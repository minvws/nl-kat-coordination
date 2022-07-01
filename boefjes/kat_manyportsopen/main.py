import json
from typing import Union, Tuple

from job import BoefjeMeta


# Until we have an implementation of bits, all logic will happen in normalizer
def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    results = {}

    return boefje_meta, json.dumps(results)
