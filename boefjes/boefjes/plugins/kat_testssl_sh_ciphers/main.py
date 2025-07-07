import os
import subprocess
from ipaddress import ip_address
from pathlib import Path


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta["arguments"]["input"]
    ip_port = input_["ip_port"]["port"]
    address = input_["ip_port"]["address"]["address"]

    if ip_address(address).version == 6:
        cmd = (
            ["/usr/local/bin/testssl.sh"] + boefje_meta["arguments"]["oci_arguments"] + ["-6", f"[{address}]:{ip_port}"]
        )
    else:
        cmd = ["/usr/local/bin/testssl.sh"] + boefje_meta["arguments"]["oci_arguments"] + [f"[{address}]:{ip_port}"]

    env = os.environ.copy()

    env["OPENSSL_TIMEOUT"] = os.getenv("TIMEOUT", "30")
    env["CONNECT_TIMEOUT"] = env["OPENSSL_TIMEOUT"]
    subprocess.run(cmd, capture_output=True, env=env)

    return [({"openkat/testssl-sh-ciphers-output"}, Path("/tmp/output.json").read_bytes())]
