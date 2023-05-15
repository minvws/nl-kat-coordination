from typing import Dict, Iterator, List, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname


def run(
    hostname: Hostname, additional_oois: List[Union[DNSARecord, DNSAAAARecord]], config: Dict[str, str]
) -> Iterator[OOI]:
    for record in additional_oois:
        yield ResolvedHostname(
            hostname=hostname.reference,
            address=record.address,
        )
