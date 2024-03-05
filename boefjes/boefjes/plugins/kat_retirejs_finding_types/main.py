import requests

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    response = requests.get(
        "https://raw.githubusercontent.com/RetireJS/retire.js/v3/repository/jsrepository.json", timeout=30
    )

    return [(set(), response.content)]
