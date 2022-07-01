from typing import Tuple, Union
import requests
from job import BoefjeMeta

API_URL = "https://admin.thegreenwebfoundation.org"


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    input_ = boefje_meta.arguments["input"]
    hostname = input_["hostname"]["name"]

    response = requests.get(f"{API_URL}/greencheck/{hostname}")

    return boefje_meta, response.content
