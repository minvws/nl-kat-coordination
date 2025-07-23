from os import getenv

import requests


def run(input_ooi: dict, boefje: dict) -> list[tuple[set, bytes | str]]:
    cve_id = input_ooi["id"]
    cveapi_url = getenv("CVEAPI_URL", "https://cve.openkat.dev/v1")
    response = requests.get(f"{cveapi_url}/{cve_id}.json", timeout=30)

    return [(set(), response.content)]
