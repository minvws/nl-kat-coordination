import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerDeclaration, NormalizerOutput


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    for declaration in json.loads(raw.decode()):
        yield NormalizerDeclaration(ooi=declaration["ooi"], end_valid_time=declaration["end_valid_time"])
