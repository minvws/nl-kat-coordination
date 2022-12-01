import json
import logging
from typing import Tuple, Union

import shodan

from os import getenv
from ipaddress import ip_address

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    api = shodan.Shodan(getenv("SHODAN_API"))
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]
    results = {}

    if ip_address(ip).is_private:
        logging.info("Private IP requested, I will not forward this to Shodan.")
    else:
        try:
            results = api.host(ip)
        except shodan.APIError as e:
            if e.args[0] != "No information available for that IP.":
                raise
            logging.info(e)

    return boefje_meta, json.dumps(results)
