import subprocess


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta["arguments"]["input"]
    hostname = input_["hostname"]["name"]

    return [
        (
            {"openkat/ssl-version-output"},
            subprocess.run(["/usr/bin/sslscan", "--xml=-", hostname], capture_output=True).stdout.decode(),
        )
    ]
