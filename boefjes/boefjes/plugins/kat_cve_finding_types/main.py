from os import getenv

import requests

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    cve_id = boefje_meta.arguments["input"]["id"]
    cveapi_url = getenv("CVEAPI_URL", "https://cve.openkat.dev/v1")
    response = requests.get(f"{cveapi_url}/{cve_id}.json", timeout=30)

    return [(set(), response.content)]
