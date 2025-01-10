from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSCNAMERecord
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname
from octopoes.models.ooi.network import Network


def nibble(cname_record: DNSCNAMERecord, resolved_hostname: ResolvedHostname) -> Iterator[OOI]:
    yield ResolvedHostname(hostname=cname_record.hostname, address=resolved_hostname.address)

    # Also the non-fqdn variant
    yield ResolvedHostname(
        hostname=Hostname(
            name=cname_record.hostname.tokenized.name,
            network=Network(name=cname_record.hostname.tokenized.network.name).reference,
        ).reference,
        address=resolved_hostname.address,
    )
