import json
from typing import Tuple, Union

from boefjes.kat_fierce.fierce import fierce, parse_args
from job import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    input_ = boefje_meta.arguments["input"]
    hostname = input_["name"]
    args = parse_args(["--domain", hostname])
    results = fierce(**vars(args))

    return boefje_meta, json.dumps(results)
