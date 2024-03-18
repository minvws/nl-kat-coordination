import json

from boefjes.job_models import BoefjeMeta


# Until we have an implementation of bits, all logic will happen in normalizer
def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    results = {}

    return [(set(), json.dumps(results))]
