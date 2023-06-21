import json
from typing import List, Tuple, Union

from cwe import Database

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    cwe_id = boefje_meta.arguments["input"]["id"]

    db = Database()
    weakness = db.get(cwe_id.split("-")[1])

    return [(set(), json.dumps(weakness.to_dict()))]
