import json
from typing import Tuple, Union

import shodan

from os import getenv
from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:

    api = shodan.Shodan(getenv("SHODAN_API"))
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]
    results = api.host(ip)

    return boefje_meta, json.dumps(results)
