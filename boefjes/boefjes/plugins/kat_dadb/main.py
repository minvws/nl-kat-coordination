"""Boefje script for getting domaions and ipaddresses from dadb"""
from os import getenv
from typing import Union, Tuple, List

import requests

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    API = getenv("DADB_API")
    access_token = getenv("DADB_ACCESS_TOKEN")
    organization = boefje_meta.organization
    response = requests.get(f"{API}/api/v1/participants/assets/{organization}?access_token={access_token}")

    return [(set(), response.content)]
