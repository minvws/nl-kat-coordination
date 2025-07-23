import json

from censys.search import CensysHosts


def run(input_ooi: dict, boefje: dict) -> list[tuple[set, bytes | str]]:
    h = CensysHosts()
    input_ = input_ooi
    ip = input_["address"]
    host = h.view(ip)

    return [(set(), json.dumps(host))]
