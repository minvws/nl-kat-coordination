import platform

import docker

from boefjes.job_models import BoefjeMeta

# FIXME: We should build a multi-platform image
if platform.machine() in ["arm64", "aarch64"]:
    WAPPALYZER_IMAGE = "noamblitz/wappalyzer:MacM1"
else:
    WAPPALYZER_IMAGE = "noamblitz/wappalyzer:latest"


def run_wappalyzer(url: str) -> str:
    client = docker.from_env()

    return client.containers.run(WAPPALYZER_IMAGE, ["wappalyzer", url], remove=True).decode()


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta.arguments["input"]

    hostname = input_["netloc"]["name"]
    path = input_["path"]
    scheme = input_["scheme"]

    url = f"{scheme}://{hostname}{path}"

    results = run_wappalyzer(url)

    return [(set(), results)]
