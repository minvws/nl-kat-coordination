import subprocess


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta["arguments"]["input"]
    hostname = input_["hostname"]["name"]

    scheme = input_["ip_service"]["service"]["name"]
    if scheme != "https":
        return [({"info/boefje"}, "Skipping check due to non-TLS scheme")]

    output = subprocess.run(["/usr/bin/sslscan", "--xml=-", hostname], capture_output=True)
    output.check_returncode()

    return [({"openkat/ssl-scan-output"}, output.stdout.decode())]
