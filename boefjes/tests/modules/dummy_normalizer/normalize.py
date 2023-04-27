from typing import Generator, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.network import Network


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Generator[OOI]:
    network = Network(name=raw.decode())

    yield network
