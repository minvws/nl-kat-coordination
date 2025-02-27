import os
import subprocess
from ipaddress import IPv6Address, ip_address

TOP_PORTS_DEFAULT = 250


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    top_ports_key = "TOP_PORTS"
    if boefje_meta["boefje"]["id"] == "nmap-udp":
        top_ports_key = "TOP_PORTS_UDP"

    top_ports = int(os.getenv(top_ports_key, TOP_PORTS_DEFAULT))
    cmd = ["nmap"] + boefje_meta["arguments"]["oci_arguments"] + ["--top-ports", str(top_ports)]

    ip = ip_address(boefje_meta["arguments"]["input"]["address"])
    if isinstance(ip, IPv6Address):
        cmd.append("-6")

    cmd.extend(["-oX", "-", str(ip)])
    output = subprocess.run(cmd, capture_output=True)

    output.check_returncode()

    return [({"openkat/nmap-output"}, output.stdout.decode())]
