import json
from typing import List, Tuple, Union

from boefjes.job_models import BoefjeMeta
from boefjes.plugins.kat_fierce.fierce import fierce, parse_args


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    hostname = input_["name"]
    args = parse_args(["--domain", hostname])
    results = fierce(**vars(args))

    return [(set(), json.dumps(results))]
