from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta

SUBFINDER_IMAGE = "projectdiscovery/subfinder:latest"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    client = docker.from_env()
    input_ = boefje_meta.arguments["input"]
    hostname = input_["name"]

    output = client.containers.run(SUBFINDER_IMAGE, ["-silent", "-active", "-d", hostname], remove=True)

    return [(set(), output)]
