from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta

NUCLEI_IMAGE = "projectdiscovery/nuclei:v2.9.1"


def verify_hostname_meta(input_):
    # if the input object is HostnameHTTPURL then the hostname is located in netloc
    if "netloc" in input_ and "name" in input_["netloc"]:
        netloc_name = input_["netloc"]["name"]
        port = input_["port"]
        return f"{netloc_name}:{port}"
    else:
        # otherwise the Hostname input object is used
        return input_["name"]


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    client = docker.from_env()

    # Checks if the url is of object HostnameHTTPURL or Hostname
    url = verify_hostname_meta(boefje_meta.arguments["input"])
    output = client.containers.run(
        NUCLEI_IMAGE,
        ["-t", "/root/nuclei-templates/cves/", "-u", url, "-jsonl"],
        remove=True,
    )

    return [(set(), output)]
