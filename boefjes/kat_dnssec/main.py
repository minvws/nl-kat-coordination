"""Boefje script checking if dnssec has been correctly configured and is valid for given hostname"""
import json
import re
from typing import Tuple, Union

import docker

from config import settings
from job import BoefjeMeta

DNSSEC_IMAGE = "noamblitz/drill:latest"


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    input_ = boefje_meta.arguments["input"]
    domain = input_["name"]

    client = docker.from_env()

    # check for string pollution in domain. This check will fail if anything other characters than a-zA-Z0-9_.- are present in the hostname
    if not re.search(r"^[\w.]+[\w\-.]+$", domain.lower()):
        raise ValueError(
            f"This domain contains prohibited characters. Are you sure you are not trying to add a url instead of a hostname?"
        )

    container = client.containers.run(
        DNSSEC_IMAGE,
        [
            "-S",
            "-k",
            "root.key",
            f"{domain}",
            f"@{settings.remote_ns}",
        ],
        detach=True,
    )

    # wait for container to exit, read its output in the logs and remove container
    container.wait()
    output = container.logs()
    container.remove()

    return boefje_meta, json.dumps(output.decode())
