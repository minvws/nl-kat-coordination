import logging
from ipaddress import ip_address

import docker
from requests import RequestException

from boefjes.job_models import BoefjeMeta
from boefjes.plugins.helpers import get_file_from_container

SSL_TEST_IMAGE = "drwetter/testssl.sh:3.2"


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta.arguments["input"]
    ip_port = input_["ip_port"]["port"]
    address = input_["ip_port"]["address"]["address"]

    if ip_address(address).version == 6:
        args = f" --jsonfile tmp/output.json --server-preference -6 [{address}]:{ip_port}"
    else:
        args = f" --jsonfile tmp/output.json --server-preference {address}:{ip_port}"

    environment_vars = {
        "OPENSSL_TIMEOUT": 30,
        "CONNECT_TIMEOUT": 30,
    }

    client = docker.from_env()
    container = client.containers.run(
        SSL_TEST_IMAGE,
        args,
        detach=True,
        environment=environment_vars,
    )

    try:
        container.wait(timeout=300)
        output = get_file_from_container(container, "tmp/output.json")
    except (docker.errors.DockerException, RequestException) as e:
        logging.warning("DockerException occurred: %s", e)
        container.stop()
        output = ""
    finally:
        container.remove()

    return [(set(), output)]
