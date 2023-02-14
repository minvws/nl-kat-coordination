from typing import Tuple, Union, List

from os import environ

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    return [(set(), repr(environ).encode())]
