from enum import Enum
from ipaddress import IPv6Address, ip_address
from os import getenv
from typing import List, Optional, Tuple, Union

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


class Protocol(Enum):
    TCP = "tcp"
    UDP = "udp"


def build_nmap_arguments(host: str, protocol: Protocol, top_ports: Optional[int]) -> List[str]:
    """Returns Nmap arguments to use based on protocol and top_ports for host."""
    ip = ip_address(host)
    args = ["--open", "-T4", "-Pn", "-r", "-v10", "-sV", "-sS" if protocol == Protocol.TCP else "-sU"]
    if top_ports is None:
        args.append("-p-")
    else:
        args.extend(["--top-ports", str(top_ports)])

    if isinstance(ip, IPv6Address):
        args.append("-6")

    args.extend(["-oX", "-", host])

    return args


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """Build Nmap arguments and return results to normalizer."""
    top_ports = int(getenv("TOP_PORTS_UDP", TOP_PORTS_DEFAULT))
    assert (
        TOP_PORTS_MIN <= top_ports <= TOP_PORTS_MAX
    ), f'{TOP_PORTS_MIN} <= {top_ports} <= {TOP_PORTS_MAX} fails. Check "TOP_PORTS" argument.'

    return [
        (
            set(),
            run_nmap(
                args=build_nmap_arguments(
                    host=boefje_meta.arguments["input"]["address"], protocol=Protocol("udp"), top_ports=top_ports
                )
            ),
        )
    ]
