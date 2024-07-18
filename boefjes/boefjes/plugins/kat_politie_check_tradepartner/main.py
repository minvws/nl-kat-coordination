import requests

from boefjes.boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    """Scrapes the politie.nl website, simply returns the data for safe-keeping.
    Posts an url, phonenumber, or ibank account"""
    input_ = boefje_meta.arguments["input"]["name"]

    url = "https://www.politie.nl/aangifte-of-melding-doen/controleer-handelspartij.html?_hn:type=action&_hn:ref=r195_r1_r1_r1"
    body = {"query": input_}

    page = requests.post(url, data=body, timeout=30)

    # while the content Might be html, its of no use to scan this for other artifacts than our tell-tale message.
    # We do store the entire output, as to collect proof of the original output of the politie.nl web-page
    return [(set(), page.text)]
