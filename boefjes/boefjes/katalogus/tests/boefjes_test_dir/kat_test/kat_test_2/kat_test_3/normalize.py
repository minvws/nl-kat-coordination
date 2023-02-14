from typing import Union, Iterator

from octopoes.models import OOI
from octopoes.models.ooi.network import Network

from boefjes.job_models import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    network = Network(name=raw.decode())

    yield network
