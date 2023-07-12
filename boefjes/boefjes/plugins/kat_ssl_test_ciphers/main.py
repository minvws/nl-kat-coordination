from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta
from boefjes.plugins.helpers import get_file_from_container

SSL_TEST_IMAGE = "drwetter/testssl.sh"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    ip_port = input_["ip_port"]["port"]
    ip_address = input_["ip_port"]["address"]["address"]

    client = docker.from_env()
    container = client.containers.run(
        SSL_TEST_IMAGE,
        f" --jsonfile tmp/output.json --server-preference {ip_address}:{ip_port}",
        detach=True,
    )

    container.wait()

    output = get_file_from_container(container, "tmp/output.json")
    # Do not crash the boefje if the output is known, instead log a warning.

    return [(set(), output)]
