import requests

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    """Scrapes the politie.nl website, and returns the website for safe-keeping.
    Posts an url, phonenumber, or ibank account"""
    ooi_hostname: str = boefje_meta.arguments["input"]["name"]

    url = "https://www.politie.nl/aangifte-of-melding-doen/controleer-handelspartij.html?_hn:type=action&_hn:ref=r195_r1_r1_r1"
    response = requests.post(
        url,
        data={
            "query": ooi_hostname,
        },
        timeout=30,
    )

    response.raise_for_status()

    return [(set(), response.text.encode())]
