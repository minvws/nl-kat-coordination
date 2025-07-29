import os
import subprocess


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    hostname = str(boefje_meta["arguments"]["input"]["netloc"])

    # Creating the URL to check
    input_ooi = boefje_meta["arguments"]["input"]
    port = f":{input_ooi['port']}" if input_ooi["port"] else ""
    url = f"{input_ooi['scheme']}://{input_ooi['netloc']['name']}{port}{input_ooi['path']}"

    # TODO: Is it okay to use human_readable here?
    git_check_cmd = ["git", "ls-remote", url]

    # See if hostname is a git repository
    subprocess.run(git_check_cmd, capture_output=True, env={"GIT_TERMINAL_PROMPT": "0"}).check_returncode()

    download_cmd = [
        "./octoscan",
        "dl",
        "--default-branch",
        "--output-dir",
        "/data/repo",
        "--org",
        "minvws",
        "--repo",
        "nl-kat-coordination",
    ]

    if "REPO_TOKEN" in os.environ:
        download_cmd.extend(["--token", os.getenv("REPO_TOKEN", "")])

    # Download the repository's GitHub action workflows
    subprocess.run(download_cmd, capture_output=True).check_returncode()

    scan_cmd = ["./octoscan", "scan", hostname, "--format", "json"]

    scan_output = subprocess.run(scan_cmd, capture_output=True)

    scan_output.check_returncode()

    return [({"openkat/nmap-output"}, scan_output.stdout.decode())]
