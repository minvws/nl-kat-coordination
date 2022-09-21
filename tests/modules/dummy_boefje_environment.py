from typing import Tuple, Union

from os import environ

from boefjes.job import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    return boefje_meta, repr(environ).encode()
