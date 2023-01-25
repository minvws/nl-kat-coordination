from typing import Union, Iterator

from octopoes.models import OOI

from boefjes.job_models import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    yield 3
