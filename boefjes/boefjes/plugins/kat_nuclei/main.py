from typing import Tuple, Union, List

import docker

from boefjes.job_models import BoefjeMeta

NUCLEI_IMAGE = "projectdiscovery/nuclei:latest"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    client = docker.from_env()
    hostnameHTTPUrl = boefje_meta.arguments["input"]
    
    hostname = hostnameHTTPUrl["netloc"]["name"]
    port = hostnameHTTPUrl["port"]

    url = f"{hostname}:{port}"
   

    output = client.containers.run(
        NUCLEI_IMAGE,
        ["-t", "/root/nuclei-templates/cves/", "-u", url, "-json"],
        remove=True,
    )

    return [(set(), output)]
