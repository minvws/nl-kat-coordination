import json
from typing import Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.certificate import Certificate
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    input_ = normalizer_meta.boefje_meta.arguments["input"]
    fqdn = input_["hostname"]["name"]
    current = f".{fqdn.lower()}"
    if current.endswith("."):
        current = current[:-1]

    internet = Network(name="internet")
    yield internet

    unique_domains = {}
    for certificate in results:
        common_name = certificate["common_name"].lower()

        # walk over all name_value parts (possibly just one, possibly more)
        names = certificate["name_value"].lower().splitlines()
        for name in names:
            if not name.endswith(current):
                # todo: do we want to hint other unrelated hostnames using the same certificate / and this possibly
                #  the same private keys for tls?
                break
            if name not in unique_domains:
                unique_domains[name] = True
                yield Hostname(name=name, network=internet.reference)

        # todo: yield only current certs?
        yield Certificate(
            subject=common_name,
            issuer=certificate["issuer_name"],
            valid_from=certificate["not_before"],
            valid_until=certificate["not_after"],
            pk_algorithm="",
            pk_size=0,  # todo: fix
            pk_number=certificate["serial_number"].upper(),
            website=None,  # This should be a hostname, not website.
            signed_by=None,
        )
        # walk over the common_name. which might be unrelated to the requested domain, or it might be a parent domain
        # which our dns Boefje should also have picked up.
        # wilcards also trigger here, and wont be visible from a DNS query
        if common_name.endswith(current) and common_name not in unique_domains:
            yield Hostname(name=common_name, network=internet.reference)
