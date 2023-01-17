import json
from typing import Tuple, Union, List

from censys.search import CensysHosts

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:

    h = CensysHosts()
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]
    host = h.view(ip)

    # return boefje_meta, json.dumps(host)
    return [(set(), json.dumps(host))]
