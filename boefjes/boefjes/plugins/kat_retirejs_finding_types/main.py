from typing import List, Tuple, Union

import requests

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    response = requests.get(
        "https://raw.githubusercontent.com/RetireJS/retire.js/v3/repository/jsrepository.json", timeout=30
    )

    return [(set(), response.content)]
