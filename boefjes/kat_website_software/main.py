from typing import Union, Tuple

import docker

from job import BoefjeMeta

WAPPALYZER_IMAGE = "noamblitz/wappalyzer:latest"


def run_wappalyzer(url: str) -> str:
    client = docker.from_env()

    return client.containers.run(
        WAPPALYZER_IMAGE, ["wappalyzer", url], remove=True
    ).decode()


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    input_ = boefje_meta.arguments["input"]

    hostname = input_["netloc"]["name"]
    path = input_["path"]
    scheme = input_["scheme"]

    url = f"{scheme}://{hostname}{path}"

    results = run_wappalyzer(url)

    return boefje_meta, results
