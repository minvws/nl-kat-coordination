"""Boefje script for scanning wordpress sites using wpscan"""
from os import getenv
from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta

WPSCAN_IMAGE = "wpscanteam/wpscan:latest"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    client = docker.from_env()
    input_ = boefje_meta.arguments["input"]

    if input_["software"]["name"] != "WordPress" or (
        "netloc" not in input_["ooi"] or "name" not in input_["ooi"]["netloc"]
    ):
        return [(set(), "")]

    hostname = input_["ooi"]["netloc"]["name"]
    path = input_["ooi"]["path"]
    scheme = input_["ooi"]["scheme"]

    if scheme != "https":
        return [(set(), "")]

    url = f"{scheme}://{hostname}{path}"

    # since wpscan can give positive exit codes on completion, docker-py's run() can fail on this
    container = client.containers.run(
        WPSCAN_IMAGE,
        [
            "--url",
            url,
            "--format",
            "json",
            "--plugins-version-detection",
            "aggressive",
            "--api-token",
            getenv("WP_SCAN_API"),
        ],
        detach=True,
    )

    try:
        # wait for container to exit, read its output in the logs and remove container
        container.wait()
        output = container.logs()
    finally:
        container.remove()

    return [(set(), output)]
