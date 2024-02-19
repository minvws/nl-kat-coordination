from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.network import Network


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    network = Network(name=raw.decode())

    yield network
