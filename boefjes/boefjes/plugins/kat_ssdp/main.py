import json
from os import getenv

from ssdpy import SSDPClient

from boefjes.job_models import BoefjeMeta

SEARCHTARGET_DEFAULT = "ssdp:all"
TIMEOUT_DEFAULT = 10


def build_arguments(host: str, ports: str) -> list[str]:
    return {
        "search_targets": int(getenv("SEARCHTARGET", SEARCHTARGET_DEFAULT)),
        "timeout": int(getenv("TIMEOUT", TIMEOUT_DEFAULT)),
    }


def run_ssdp(search_targets: str, timeout: int):
    client = SSDPClient()
    return client.m_search(st=search_targets, mx=timeout)


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    return [
        (
            set(),
            json.dumps(run_ssdp(**build_arguments())),
        )
    ]
