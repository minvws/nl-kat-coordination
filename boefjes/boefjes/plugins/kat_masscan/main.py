import logging
import os
import subprocess


def run_masscan(target_ip: str) -> bytes:
    # Scan according to arguments.
    port_range = os.getenv("PORTS", "53,80,443")
    max_rate = os.getenv("MAX_RATE", 100)
    logging.info("Running masscan...")
    cmd = ["/home/lama/masscan/bin/masscan", "-p", port_range, "--max-rate", max_rate, "-oJ", "/dev/stdout", target_ip]
    return subprocess.run(cmd, capture_output=True).stdout


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    """Creates webpage and takes capture using Playwright container."""
    input_ = boefje_meta["arguments"]["input"]
    ip_range = f"{input_['start_ip']['address']}/{str(input_['mask'])}"
    m_run = run_masscan(target_ip=ip_range)
    logging.info("Received a response with length %d", len(m_run))

    return [({"openkat/masscan-output"}, m_run)]
