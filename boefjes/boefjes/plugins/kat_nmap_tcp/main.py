from ipaddress import IPv6Address, ip_address
import os
import subprocess


TOP_PORTS_DEFAULT = 250


def run(boefje_meta: dict):
    top_ports = int(os.getenv("TOP_PORTS", TOP_PORTS_DEFAULT))
    cmd = ["nmap"] + boefje_meta["arguments"]["oci_arguments"] + ["--top-ports", str(top_ports)]

    ip = ip_address(boefje_meta["arguments"]["input"]["address"])
    if isinstance(ip, IPv6Address):
        cmd.append("-6")

    cmd.extend(["-oX", "-", str(ip)])
    return [(set(), subprocess.run(cmd, capture_output=True).stdout.decode())]
