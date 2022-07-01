from enum import Enum
from ipaddress import ip_address, IPv6Address
from typing import List, Tuple, Union, Optional

import docker

from job import BoefjeMeta

NMAP_IMAGE = "instrumentisto/nmap:latest"


def run_nmap(args: List[str]) -> str:
    client = docker.from_env()
    return client.containers.run(NMAP_IMAGE, args, remove=True).decode()


class Protocol(Enum):
    TCP = "tcp"
    UDP = "udp"


def build_nmap_arguments(host: str, protocol: Protocol, top_ports: Optional[int]):
    ip = ip_address(host)
    args = ["nmap"]

    if protocol == Protocol.TCP:
        args.extend(["-T4", "-Pn", "-r", "-v10", "-sV", "-sS"])
    else:
        args.extend(["-T4", "-Pn", "-r", "-v10", "-sV", "-sU"])

    if top_ports is not None:
        args.extend(["--top-ports", str(top_ports)])
    elif protocol == Protocol.TCP:
        args.append("-p-")

    if isinstance(ip, IPv6Address):
        args.append("-6")

    args.extend(["-oX", "-", host])

    return args


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    input_ = boefje_meta.arguments["input"]
    host = input_["address"]

    # protocol = boefje_meta.arguments["protocol"]
    # top_ports = boefje_meta.arguments.get("top_ports", None)
    top_ports = 250
    protocol = "tcp"
    args = build_nmap_arguments(host, Protocol(protocol), top_ports)

    return boefje_meta, run_nmap(args)
