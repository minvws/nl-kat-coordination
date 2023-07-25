import json
from typing import List, Tuple, Union

from boefjes.job_models import BoefjeMeta

FINDING_TYPE_PATH = "boefjes/plugins/kat_kat_finding_types/kat_finding_types.json"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    with open(FINDING_TYPE_PATH) as json_file:
        data = json.load(json_file)
        return [(set(), json.dumps(data))]
