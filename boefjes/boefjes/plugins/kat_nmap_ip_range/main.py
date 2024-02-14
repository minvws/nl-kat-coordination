from ipaddress import IPv6Network, ip_network
from os import getenv

import docker

from boefjes.job_models import BoefjeMeta

NMAP_IMAGE = "instrumentisto/nmap:latest"
TOP_PORTS_MAX = 65535
TOP_PORTS_DEFAULT = 250
TOP_PORTS_MIN = 1


def run_nmap(args: list[str]) -> str:
    """Run Nmap in Docker."""
    client = docker.from_env()
    return client.containers.run(NMAP_IMAGE, args, remove=True).decode()


def build_nmap_arguments(ip_range: str, top_ports: int, protocol_str: str) -> list[str]:
    """Build nmap arguments from the hosts IP with the required ports."""
    if protocol_str not in ["S", "U"]:
        raise ValueError('Protocol should be "S" or "U"')
    if not TOP_PORTS_MIN <= top_ports <= TOP_PORTS_MAX:
        raise ValueError(f"{TOP_PORTS_MIN} <= TOP_PORTS: {top_ports} <= {TOP_PORTS_MAX} is invalid.")

    args = ["nmap", "--open", "-T4", "-Pn", "-r", "-v10", f"-s{protocol_str}", "--top-ports", str(top_ports)]
    if isinstance(ip_network(ip_range), IPv6Network):
        args.append("-6")
    args.extend(["-oX", "-", ip_range])

    return args


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    """Build Nmap arguments and return results to normalizer."""
    ip_range = f"{boefje_meta.arguments['input']['start_ip']['address']}/{str(boefje_meta.arguments['input']['mask'])}"
    top_ports_tcp = int(getenv("TOP_PORTS_TCP", 250))
    top_ports_udp = int(getenv("TOP_PORTS_UDP", 10))
    if not top_ports_tcp and not top_ports_udp:
        raise ValueError("At least one TOP_PORTS argument should be non-zero")

    results = []
    if top_ports_tcp:
        results.append(run_nmap(build_nmap_arguments(ip_range=ip_range, top_ports=top_ports_tcp, protocol_str="S")))
    if top_ports_udp:
        results.append(run_nmap(build_nmap_arguments(ip_range=ip_range, top_ports=top_ports_udp, protocol_str="U")))

    return [(set(), "\n\n".join(results))]
