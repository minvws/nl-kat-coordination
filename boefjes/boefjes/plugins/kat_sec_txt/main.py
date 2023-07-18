import json
import requests
from typing import List, Tuple, Union
from sectxt import SecurityTXT

from boefjes.job_models import BoefjeMeta

# EXPECTED_PATH = "/.well-known/security.txt"
# LEGACY_PATH = "/security.txt"
MAX_LEN = 100 * 1024

def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    host = input_["name"]

    # url = "https://" + str(host) + EXPECTED_PATH
    # response = requests.get(url)

    # if response.status_code != 200:
    #     url = "https://" + str(host) + LEGACY_PATH
    #     response = requests.get(url)

    # secTXT = SecurityTXT(url)
    secTXT = SecurityTXT(str(host))
    results = { 
    "valid": secTXT.is_valid(),
    "errors": secTXT.errors,
    }

    return [(set(), json.dumps(results))]