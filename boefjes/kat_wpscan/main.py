"""Boefje script for scanning wordpress sites using wpscan"""
from typing import Union, Tuple

import docker

from config import settings
from job import BoefjeMeta

WPSCAN_IMAGE = "wpscanteam/wpscan:latest"


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    client = docker.from_env()
    input_ = boefje_meta.arguments["input"]

    if not input_["software"]["name"] == "WordPress" or (
        not "netloc" in input_["ooi"] or not "name" in input_["ooi"]["netloc"]
    ):
        return boefje_meta, ""

    hostname = input_["ooi"]["netloc"]["name"]
    path = input_["ooi"]["path"]
    scheme = input_["ooi"]["scheme"]

    if not scheme == "https":
        return boefje_meta, ""

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
            settings.wp_scan_api,
        ],
        detach=True,
    )

    # wait for container to exit, read its output in the logs and remove container
    container.wait()
    output = container.logs()
    container.remove()

    return boefje_meta, output
