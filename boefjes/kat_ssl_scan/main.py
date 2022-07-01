from typing import Tuple, Union

import docker

from job import BoefjeMeta

SSLSCAN_IMAGE = "breezethink/sslscan:latest"


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    client = docker.from_env()
    input_ = boefje_meta.arguments["input"]
    hostname = input_["hostname"]["name"]

    output = client.containers.run(SSLSCAN_IMAGE, ["--xml=-", hostname], remove=True)

    return boefje_meta, output
