import logging
from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta
from boefjes.plugins.helpers import get_file_from_container

logger = logging.getLogger(__name__)

OCI_IMAGE = "ghcr.io/minvws/nl-kat-chrome-crawler-mitmproxy:latest"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]

    hostname = input_["netloc"]["name"]
    path = input_["path"]
    scheme = input_["scheme"]

    url = f"{scheme}://{hostname}{path}"

    command = f"/usr/local/bin/sitecrawler -o output -u {url}"

    logger.debug("Running container with command %s", command)

    client = docker.from_env()
    container = client.containers.run(
        OCI_IMAGE,
        command=command,
        detach=True,
    )

    container.wait()

    logfile = get_file_from_container(container, "/app/output/log.txt")

    for line in logfile.decode("utf-8").splitlines():
        logging.debug("Container output: %s", line)

    output = get_file_from_container(container, "/app/output/dump.har")

    try:
        container.remove()
    except Exception as e:
        logging.warning(e)

    return [(set(["har"]), output)]
