from ipaddress import IPv6Address, ip_address
import os
import subprocess


TOP_PORTS_DEFAULT = 250


def build_nmap_cmd(host: str, top_ports: int) -> list[str]:
    """Returns Nmap arguments to use based on protocol and top_ports for host."""
    ip = ip_address(host)
    args = ["nmap", "--open", "-T4", "-Pn", "-r", "-v10", "-sV", "-sS", "--top-ports", str(top_ports)]

    if isinstance(ip, IPv6Address):
        args.append("-6")

    args.extend(["-oX", "-", host])

    return args


def run(boefje_meta: dict):
    top_ports = int(os.getenv("TOP_PORTS", TOP_PORTS_DEFAULT))

    cmd = build_nmap_cmd(boefje_meta["arguments"]["input"]["address"], top_ports)
    output = subprocess.run(cmd, capture_output=True)

    return [(set(), output.stdout.decode())]
