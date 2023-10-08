import logging
from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta
from boefjes.plugins.helpers import get_file_from_container

OCI_IMAGE = "lapje"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    url = input_["url"]

    command = f"/usr/local/bin/sitecrawler -o output -u {url}"

    client = docker.from_env()
    container = client.containers.run(
        OCI_IMAGE,
        command=command,
        detach=True,
    )

    container.wait()

    output = get_file_from_container(container, "output/network.mproxy")

    try:
        container.remove()
    except Exception as e:
        logging.warning(e)

    return [(set(), output)]
