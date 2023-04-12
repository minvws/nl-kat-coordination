from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSARecord, DNSAAAARecord
from octopoes.models.ooi.dns.zone import ResolvedHostname, Hostname


def run(
    hostname: Hostname,
    additional_oois: List[Union[DNSARecord, DNSAAAARecord]],
) -> Iterator[OOI]:
    for record in additional_oois:
        yield ResolvedHostname(
            hostname=hostname.reference,
            address=record.address,
        )
