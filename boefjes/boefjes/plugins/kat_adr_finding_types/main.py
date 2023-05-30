from typing import List, Tuple, Union

import requests

from boefjes.job_models import BoefjeMeta

FINDING_TYPES_JSON_LOCATION = (
    "https://raw.githubusercontent.com/minvws/nl-kat-coordination/finding-types-in-octopoes/adr_finding_types.json"
)


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    response = requests.get(f"{FINDING_TYPES_JSON_LOCATION}")

    return [(set(), response.content)]
