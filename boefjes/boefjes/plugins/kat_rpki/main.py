"""Boefje script for validating vrps records based on code from @trideeindhoven"""
import json
from datetime import datetime
from typing import List, Tuple, Union

from netaddr import IPAddress, IPNetwork

from boefjes.job_models import BoefjeMeta

FINDING_TYPE_PATH = "boefjes/plugins/kat_rpki/rpki.json"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]

    with open(FINDING_TYPE_PATH) as json_file:
        rpki_json = json.load(json_file)

    exists = False
    valid = False
    roas = []
    for roa in rpki_json["roas"]:
        if IPAddress(ip) in IPNetwork(roa["prefix"]):
            exists = True
            expires = datetime.fromtimestamp(roa["expires"])
            roas.append({"prefix": roa["prefix"], "expires": expires.strftime("%Y-%m-%dT%H:%M"), "ta": roa["ta"]})
            if expires > datetime.utcnow():
                valid = True

    results = {"vrps_records": roas, "valid": valid, "exists": exists}

    return [(set(), json.dumps(results))]
