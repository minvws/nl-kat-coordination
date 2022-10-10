import json
from typing import Tuple, Union

import censys

from censys.search import CensysHosts
from boefjes.job import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:

    h = CensysHosts()
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]
    host = h.view(ip)

    return boefje_meta, json.dumps(host)
