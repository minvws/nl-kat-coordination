from typing import List, Tuple, Union

import requests

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    cve_id = boefje_meta.arguments["input"]["id"]
    response = requests.get(f"https://v1.cveapi.com/{cve_id}.json")

    return [(set(), response.content)]
