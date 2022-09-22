from typing import Tuple, Union

from boefjes.job import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    raise RuntimeError("dummy error")
