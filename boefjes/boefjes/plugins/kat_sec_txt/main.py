import json
from typing import List, Tuple, Union

from sectxt import SecurityTXT

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    host = input_["name"]

    secTXT = SecurityTXT(str(host))
    results = {
        "valid": secTXT.is_valid(),
        "errors": secTXT.errors,
    }

    return [(set(), json.dumps(results))]
