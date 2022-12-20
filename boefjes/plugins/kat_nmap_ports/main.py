from os import getenv
from ipaddress import ip_address, IPv6Address
from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta

NMAP_IMAGE = "instrumentisto/nmap:latest"


def run_nmap(args: List[str]) -> str:
    """Run Nmap in Docker."""
    client = docker.from_env()
    return client.containers.run(NMAP_IMAGE, args, remove=True).decode()


def build_nmap_arguments(host: str, ports: str):
    """Build nmap arguments from the hosts IP with the required ports."""
    ip = ip_address(host)
    args = ["nmap", "-T4", "-Pn", "-r", "-v10", "-sV", "-sS", "-sU", f"-p{ports}"]
    if isinstance(ip, IPv6Address):
        args.append("-6")
    args.extend(["-oX", "-", host])

    return args


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """Build the required Nmap arguments and return results to the normalizer."""
    input_ = boefje_meta.arguments["input"]
    host = input_["address"]
    ports = getenv("PORTS")
    if ports is None:
        raise ValueError('"PORTS" argument is not specified.')
    # Maybe more validation on the ports variable is needed here but
    # it is quite flexible according to the Nmap documentation.
    return [(set(), run_nmap(build_nmap_arguments(host, ports)))]
