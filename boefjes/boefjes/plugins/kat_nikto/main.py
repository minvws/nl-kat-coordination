import json
import logging
import os

from pydantic import BaseModel


class Vulnerability(BaseModel):
    id: str
    method: str
    msg: str


def run(boefje_meta: dict):
    file_path = os.path.join("./", "output.json")
    if not os.path.isfile(file_path):
        raise Exception("output.json file does not exist. Has the kat_nikto image given an error?")

    with open(file_path) as f:
        json_data = json.loads(f.read())[0]
        found_vulnerabilities = [Vulnerability.model_validate(x) for x in json_data["vulnerabilities"]]
    logging.info(found_vulnerabilities)

    return [(set(), "a")]
