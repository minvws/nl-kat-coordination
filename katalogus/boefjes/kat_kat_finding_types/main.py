import json

FINDING_TYPE_PATH = "boefjes/plugins/kat_kat_finding_types/kat_finding_types.json"


def run(input_ooi: dict, boefje: dict) -> list[tuple[set, bytes | str]]:
    with open(FINDING_TYPE_PATH) as json_file:
        data = json.load(json_file)
        return [(set(), json.dumps(data))]
