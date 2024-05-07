import json
import os
import re
import subprocess


def run(boefje_meta: dict):
    input_ = boefje_meta["arguments"]["input"]
    domain = input_["name"]

    # check for string pollution in domain. This check will fail if anything other characters than a-zA-Z0-9_.- are
    # present in the hostname
    if not re.search(r"^[\w.]+[\w\-.]+$", domain.lower()):
        raise ValueError(
            "This domain contains prohibited characters. Are you sure you are not trying to add a url instead of a "
            "hostname?"
        )

    remote_ns = os.getenv("REMOTE_NS", "1.1.1.1")
    cmd = ["/usr/bin/drill", "-S", "-k", "root.key", str(domain), "@" + remote_ns]
    output = subprocess.run(cmd, capture_output=True)

    results = json.dumps(output.stdout.decode())
    return [(set(), results)]
