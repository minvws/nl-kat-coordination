import json
from io import StringIO
from typing import Union, Iterator

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname, SimilarHostname
from octopoes.models.ooi.network import Network


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    internet = Network(name="internet")
    yield internet

    stream = StringIO(raw.decode())

    for line in stream:
        data = json.loads(line)
        hostname = Hostname(network=internet.reference, name=data["domain"])
        similar_to = Hostname(network=internet.reference, name=data["match"])
        similar_hostname = SimilarHostname(hostname=hostname.reference, similar_to=similar_to.reference)

        yield from [hostname, similar_to, similar_hostname]
