from typing import List, Tuple, Union

import requests

from boefjes.job_models import BoefjeMeta

API_URL = "https://admin.thegreenwebfoundation.org"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    hostname = input_["hostname"]["name"]

    response = requests.get(f"{API_URL}/greencheck/{hostname}")

    return [(set(), response.content)]
