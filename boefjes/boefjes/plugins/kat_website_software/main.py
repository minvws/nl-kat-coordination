import platform
from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta

# FIXME: We should build a multi-platform image
if platform.processor() == "arm":
    WAPPALYZER_IMAGE = "noamblitz/wappalyzer:MacM1"
else:
    WAPPALYZER_IMAGE = "noamblitz/wappalyzer:latest"


def run_wappalyzer(url: str) -> str:
    client = docker.from_env()

    return client.containers.run(WAPPALYZER_IMAGE, ["wappalyzer", url], remove=True).decode()


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]

    hostname = input_["netloc"]["name"]
    path = input_["path"]
    scheme = input_["scheme"]

    url = f"{scheme}://{hostname}{path}"

    results = run_wappalyzer(url)

    return [(set(), results)]
