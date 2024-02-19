import json

from boefjes.job_models import BoefjeMeta
from boefjes.plugins.kat_fierce.fierce import fierce, parse_args


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta.arguments["input"]
    hostname = input_["name"]
    args = parse_args(["--domain", hostname])
    results = fierce(**vars(args))

    return [(set(), json.dumps(results))]
