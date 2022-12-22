import datetime
import json
from typing import Iterator, Union
from dateutil.parser import parse
from octopoes.models import OOI
from octopoes.models.ooi.certificate import Certificate
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network

from boefjes.job_models import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    input_ = normalizer_meta.raw_data.boefje_meta.arguments["input"]
    fqdn = input_["hostname"]["name"]
    current = fqdn.lstrip(".").rstrip(".")

    network = Network(name="internet")
    yield network
    network_reference = network.reference

    unique_domains = set()
    for certificate in results:
        common_name = certificate["common_name"].lower().lstrip(".*")

        # walk over all name_value parts (possibly just one, possibly more)
        names = certificate["name_value"].lower().splitlines()
        for name in names:
            if not name.endswith(current):
                # todo: do we want to hint other unrelated hostnames using the same certificate / and this possibly
                #  the same private keys for tls?
                pass
            if name not in unique_domains:
                yield Hostname(name=name, network=network_reference)
                unique_domains.add(name)

        # todo: yield only current certs?
        yield Certificate(
            subject=common_name,
            issuer=certificate["issuer_name"],
            valid_from=certificate["not_before"],
            valid_until=certificate["not_after"],
            serial_number=certificate["serial_number"].upper(),
            expires_in=parse(certificate["not_after"]).astimezone(datetime.timezone.utc)
            - datetime.datetime.now(datetime.timezone.utc),
        )
        # walk over the common_name. which might be unrelated to the requested domain, or it might be a parent domain
        # which our dns Boefje should also have picked up.
        # wilcards also trigger here, and wont be visible from a DNS query
        if common_name.endswith(current) or common_name not in unique_domains:
            yield Hostname(name=common_name, network=network_reference)
