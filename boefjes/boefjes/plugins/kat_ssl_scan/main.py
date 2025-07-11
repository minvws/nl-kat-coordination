import subprocess


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta["arguments"]["input"]
    hostname = input_["hostname"]["name"]

    output = subprocess.run(["/usr/bin/sslscan", "--xml=-", hostname], capture_output=True)
    output.check_returncode()

    return [({"openkat/ssl-version-output"}, output.stdout.decode())]
