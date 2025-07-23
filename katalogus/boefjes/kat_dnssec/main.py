import re
import subprocess


def run(input_ooi: dict, boefje: dict) -> list[tuple[set, bytes | str]]:
    domain = input_ooi["name"]

    # check for string pollution in domain. This check will fail if anything other characters than a-zA-Z0-9_.- are
    # present in the hostname
    if not re.search(r"^[\w.]+[\w\-.]+$", domain.lower()):
        raise ValueError(
            "This domain contains prohibited characters. Are you sure you are not trying to add a url instead of a "
            "hostname?"
        )

    cmd = ["/usr/bin/drill", "-DT", domain]
    output = subprocess.run(cmd, capture_output=True)

    output.check_returncode()

    return [({"openkat/dnssec-output"}, output.stdout)]
