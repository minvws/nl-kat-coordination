from typing import Tuple, Union

import docker

from job import BoefjeMeta

OPENSSL_IMAGE = "securefab/openssl:latest"


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    client = docker.from_env()
    input_ = boefje_meta.arguments["input"]
    hostname = input_["hostname"]["name"]

    try:
        output = client.containers.run(
            OPENSSL_IMAGE,
            [
                "s_client",
                "-host",
                hostname,
                "-port",
                "443",
                "-prexit",
                "-showcerts",
                "-servername",
                hostname,
            ],
            remove=True,
        )
    except docker.errors.ContainerError as e:
        output = f"error {str(e)}"

    return boefje_meta, output
