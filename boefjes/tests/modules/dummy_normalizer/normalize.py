from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models.ooi.network import Network


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    network = Network(name=raw.decode())

    yield network
