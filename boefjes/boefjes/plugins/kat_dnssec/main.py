"""Boefje script checking if dnssec has been correctly configured and is valid for given hostname"""
import json
import re
from typing import List, Tuple, Union

import docker

from boefjes.config import settings
from boefjes.job_models import BoefjeMeta

DNSSEC_IMAGE = "noamblitz/drill:latest"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    domain = input_["name"]

    client = docker.from_env()

    # check for string pollution in domain. This check will fail if anything other characters than a-zA-Z0-9_.- are
    # present in the hostname
    if not re.search(r"^[\w.]+[\w\-.]+$", domain.lower()):
        raise ValueError(
            "This domain contains prohibited characters. Are you sure you are not trying to add a url instead of a "
            "hostname?"
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

    try:
        # wait for container to exit, read its output in the logs and remove container
        container.wait()
        output = container.logs()
    finally:
        container.remove()

    results = json.dumps(output.decode())
    return [(set(), results)]
