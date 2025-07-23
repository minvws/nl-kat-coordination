import os
import subprocess
from ipaddress import IPv6Address, ip_address

TOP_PORTS_DEFAULT = 250


def run(input_ooi: dict, boefje) -> list[tuple[set, bytes | str]]:
    top_ports_key = "TOP_PORTS"
    if boefje["id"] == "nmap-udp":
        top_ports_key = "TOP_PORTS_UDP"

    top_ports = int(os.getenv(top_ports_key, TOP_PORTS_DEFAULT))
    cmd = ["nmap"] + boefje["oci_arguments"] + ["--top-ports", str(top_ports)]

    address = input_ooi["address"]

    ip = ip_address(address)
    if isinstance(ip, IPv6Address):
        cmd.append("-6")

    cmd.extend(["-oX", "-", str(ip)])
    output = subprocess.run(cmd, capture_output=True)

    output.check_returncode()

    return [({"openkat/nmap-output"}, output.stdout.decode())]
