from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    yield {
        "I": "write",
        "bad": "normalizers",
    }
