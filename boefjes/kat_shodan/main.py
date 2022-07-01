import json
from typing import Tuple, Union

import shodan

from config import settings
from job import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:

    api = shodan.Shodan(settings.shodan_api)
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]
    results = api.host(ip)

    return boefje_meta, json.dumps(results)
