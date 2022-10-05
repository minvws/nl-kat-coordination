import json
from typing import Iterator, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.network import IPPort, Protocol, PortState

from boefjes.job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    ooi = Reference.from_str(normalizer_meta.boefje_meta.input_ooi)

    for scan in results["services"]:
        port_nr = scan["port"]
        transport = scan["transport_protocol"].lower()

        ip_port = IPPort(
            address=ooi,
            protocol=Protocol(transport),
            port=int(port_nr),
            state=PortState("open"),
        )
        yield ip_port

