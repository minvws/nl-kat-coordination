from ipaddress import ip_address
from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta
from boefjes.plugins.helpers import get_file_from_container

SSL_TEST_IMAGE = "drwetter/testssl.sh:3.2"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    ip_port = input_["ip_port"]["port"]
    address = input_["ip_port"]["address"]["address"]

    if ip_address(address).version == 6:
        args = f" --jsonfile tmp/output.json --server-preference -6 [{address}]:{ip_port}"
    else:
        args = f" --jsonfile tmp/output.json --server-preference {address}:{ip_port}"

    client = docker.from_env()
    container = client.containers.run(
        SSL_TEST_IMAGE,
        args,
        detach=True,
    )

    container.wait()

    output = get_file_from_container(container, "tmp/output.json")

    return [(set(), output)]
