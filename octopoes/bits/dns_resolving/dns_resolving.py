from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSARecord, DNSAAAARecord
from octopoes.models.ooi.dns.zone import ResolvedHostname, Hostname


def run(
    hostname: Hostname,
    additional_oois: List[Union[DNSARecord, DNSAAAARecord]],
) -> Iterator[OOI]:

    # only run bit on fqdns
    if not hostname.name.endswith("."):
        return

    non_fqdn_hostname = Hostname(network=hostname.network, name=hostname.name.rstrip("."))
    yield non_fqdn_hostname

    for record in additional_oois:
        for hostname_ in [hostname, non_fqdn_hostname]:
            yield ResolvedHostname(
                hostname=hostname_.reference,
                address=record.address,
            )
