import json

from katalogus.boefjes.kat_fierce.fierce import fierce, parse_args


def run(input_ooi: dict, boefje: dict) -> list[tuple[set, bytes | str]]:
    input_ = input_ooi
    hostname = input_["name"]
    args = parse_args(["--domain", hostname])
    results = fierce(**vars(args))

    return [(set(), json.dumps(results))]
