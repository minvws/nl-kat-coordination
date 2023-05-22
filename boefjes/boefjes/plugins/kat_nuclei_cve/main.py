from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta

NUCLEI_IMAGE = "projectdiscovery/nuclei:v2.9.4"


def verify_hostname_meta(input_ooi):
    # if the input object is HostnameHTTPURL then the hostname is located in netloc
    if "netloc" in input_ooi and "name" in input_ooi["netloc"]:
        netloc_name = input_ooi["netloc"]["name"]
        port = input_ooi["port"]
        return f"{netloc_name}:{port}"
    else:
        # otherwise the Hostname input object is used
        return input_ooi["name"]


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    client = docker.from_env()

    # Checks if the url is of object HostnameHTTPURL or Hostname
    url = verify_hostname_meta(boefje_meta.arguments["input"])
    output = client.containers.run(
        NUCLEI_IMAGE,
        ["-t", "/root/nuclei-templates/http/cves/", "-u", url, "-jsonl"],
        remove=True,
    )

    return [(set(), output)]
