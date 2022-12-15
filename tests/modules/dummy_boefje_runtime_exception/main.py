from typing import Tuple, Union, List

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    raise RuntimeError("dummy error")
