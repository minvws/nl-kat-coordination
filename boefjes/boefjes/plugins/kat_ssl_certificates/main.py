from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta

OPENSSL_IMAGE = "alpine/openssl:latest"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    client = docker.from_env()
    input_ = boefje_meta.arguments["input"]
    hostname = input_["hostname"]["name"]
    ip_address = input_["ip_service"]["ip_port"]["address"]["address"]
    port = input_["ip_service"]["ip_port"]["port"]

    try:
        output = client.containers.run(
            OPENSSL_IMAGE,
            [
                "s_client",
                "-host",
                ip_address,
                "-port",
                port,
                "-prexit",
                "-showcerts",
                "-servername",
                hostname,
            ],
            remove=True,
        )
    except docker.errors.ContainerError as e:
        output = f"error {str(e)}"

    return [(set(), output)]
