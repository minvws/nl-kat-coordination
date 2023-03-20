from typing import Tuple, Union, List

import docker

from boefjes.job_models import BoefjeMeta

NUCLEI_IMAGE = "projectdiscovery/nuclei:latest"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    client = docker.from_env()
    input_ = boefje_meta.arguments["input"]
    url = input_["name"]

    output = client.containers.run(
        NUCLEI_IMAGE,
        ["-t", "/root/nuclei-templates/cves/", "-u", url, "-json"],
        remove=True,
    )

    return [(set(), output)]
