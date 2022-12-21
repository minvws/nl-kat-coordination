import re

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


def build_nmap_arguments(host: str, ports: str) -> str:
    """Build nmap arguments from the hosts IP with the required ports."""
    ip = ip_address(host)
    args = ["nmap", "-T4", "-Pn", "-r", "-v10", "-sV", "-sS", "-sU", f"-p{ports}"]
    if isinstance(ip, IPv6Address):
        args.append("-6")
    args.extend(["-oX", "-", host])

    return args


def get_ports(
    valid=re.compile(
        "\\s*([TUSP]:)?(\\d+|[a-z*?]+|(\\[?\\d*-\\d*\\]?))(,(([TUSP]:)|\\s)?(\\d+|[a-z*?]+|(\\[?\\d*-\\d*\\]?)))*"
    ),
) -> str:
    """Returns ports argument if valid. Double slashes are for flake8 W605.

    A valid port is:
    - a single port (set of digits) {22}
        - Regex: \\d+
    - a port range (optional digits separated by hypen, optionally bracketed) {[80-]}
        - Regex: (\\[?\\d*-\\d*\\]?)
    - a valid Nmap protocol (alfanumeric wildcarded lowercase) {https*}
        - Regex: [a-z*?]+

    There needs to be at least one valid port. Multiple ports can be separated by a comma (',').
    A port can be preceded by 'T:', 'U:', 'S:' or 'P:' to specify a protocol
        - Regex: ([TUSP]:)?
    There can be spaces between the flag and its arguments.
        - Regex: \\s*

    Regex: "\\s*([TUSP]:)?(\\d+|[a-z*?]+|(\\[?\\d*-\\d*\\]?))(,(([TUSP]:)|\\s)?(\\d+|[a-z*?]+|(\\[?\\d*-\\d*\\]?)))*"

    See also: https://nmap.org/book/port-scanning-options.html.
    """
    ports = getenv("PORTS")
    assert ports is not None, '"PORTS" argument is not specified.'
    assert valid.fullmatch(ports) is not None, f'Invalid PORTS argument "{ports}"'
    return ports


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """Build Nmap arguments and return results to normalizer."""
    return [(set(), run_nmap(build_nmap_arguments(host=boefje_meta.arguments["input"]["address"], ports=get_ports())))]
