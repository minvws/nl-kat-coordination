import json
from typing import Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.network import IPAddressV4, Network, IPV4NetBlock
from octopoes.models.ooi.dns.zone import Hostname
from boefjes.job_models import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    internet = Network(name="internet")
    for address in results["ip_addresses"]:
        if "/" in address:
            ip, mask = address["ip_address"].split("/")
            ip_address = IPAddressV4(address=ip, network=internet.reference)
            yield ip_address
            yield IPV4NetBlock(start_ip=ip_address.reference, mask=mask)
        else:
            yield IPAddressV4(address=address["ip_address"], network=internet.reference)

    for hostname in results["domains"]:
        yield Hostname(name=hostname["domain"], network=internet.reference)
