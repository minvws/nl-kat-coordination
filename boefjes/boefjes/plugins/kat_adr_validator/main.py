from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta


ADR_VALIDATOR_REPOSITORY = "registry.gitlab.com/commonground/don/adr-validator/tmp"
ADR_VALIDATOR_VERSION = "main"


def run_adr_validator(url: str) -> str:
    client = docker.from_env()
    image = f"{ADR_VALIDATOR_REPOSITORY}:{ADR_VALIDATOR_VERSION}"
    args = ("-format", "json", url)

    return client.containers.run(image, args, remove=True, read_only=True)


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input = boefje_meta.arguments["input"]
    api_url = input["api_url"]

    hostname = api_url["netloc"]["name"]
    path = api_url["path"]
    scheme = api_url["scheme"]

    url = f"{scheme}://{hostname}{path}"

    output = run_adr_validator(url)

    return [
        (
            set(),
            output,
        ),
    ]
