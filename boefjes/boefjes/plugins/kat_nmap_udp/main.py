from ipaddress import IPv6Address, ip_address
from os import getenv
from typing import List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta

NMAP_IMAGE = "instrumentisto/nmap:latest"
TOP_PORTS_MAX = 65535
TOP_PORTS_DEFAULT = 250
TOP_PORTS_MIN = 1


def run_nmap(args: List[str]) -> str:
    """Run Nmap in Docker."""
    client = docker.from_env()
    return client.containers.run(NMAP_IMAGE, args, remove=True).decode()


def build_nmap_arguments(host: str, top_ports: int) -> List[str]:
    """Returns Nmap arguments to use based on protocol and top_ports for host."""
    ip = ip_address(host)
    args = ["--open", "-T4", "-Pn", "-r", "-v10", "-sV", "-sU", "--top-ports", str(top_ports)]

    if isinstance(ip, IPv6Address):
        args.append("-6")

    args.extend(["-oX", "-", host])

    return args


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """Build Nmap arguments and return results to normalizer."""
    top_ports = int(getenv("TOP_PORTS", TOP_PORTS_DEFAULT))

    return [
        (
            set(),
            run_nmap(
                args=build_nmap_arguments(
                    host=boefje_meta.arguments["input"]["address"],
                    top_ports=top_ports,
                )
            ),
        )
    ]
