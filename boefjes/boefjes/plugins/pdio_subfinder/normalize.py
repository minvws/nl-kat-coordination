from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    hostname_ooi_reference = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)
    network_reference = Network(name=hostname_ooi_reference.tokenized.network.name).reference

    for hostname in raw.splitlines():
        hostname_ooi = Hostname(name=hostname, network=network_reference)
        yield hostname_ooi
