from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    yield {
        "I": "write",
        "bad": "normalizers",
    }
