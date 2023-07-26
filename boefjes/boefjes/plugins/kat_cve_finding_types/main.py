from os import getenv
from typing import List, Tuple, Union

import requests

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    cve_id = boefje_meta.arguments["input"]["id"]
    cveapi_url = getenv("CVEAPI_URL", "https://cve.openkat.dev/v1")
    response = requests.get(f"{cveapi_url}/{cve_id}.json")

    return [(set(), response.content)]
