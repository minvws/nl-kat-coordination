from typing import Tuple, Union

from job import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    return boefje_meta, b"dummy-data"
