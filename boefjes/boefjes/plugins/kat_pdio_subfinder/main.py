import logging
import os
import subprocess


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    """Create image from docker and run subfinder with only active domains output."""
    rate_limit = int(os.getenv("SUBFINDER_RATE_LIMIT", "0"))
    input_ = boefje_meta["arguments"]["input"]
    hostname = input_["name"]

    logging.info("Using subfinder with rate limit %s on %s", rate_limit, hostname)

    return [
        (
            {"openkat/pdio-subfinder"},
            subprocess.run(
                ["/usr/local/bin/subfinder", "-silent", "-active", "-rate-limit", str(rate_limit), "-d", hostname],
                capture_output=True,
            ).stdout.decode(),
        )
    ]
