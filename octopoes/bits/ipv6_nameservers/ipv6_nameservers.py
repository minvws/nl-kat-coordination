from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord, DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import KATFindingType, Finding


def run(
    hostname: Hostname,
    additional_oois: List[Union[DNSAAAARecord, DNSARecord]],
) -> Iterator[OOI]:

    dns_ns_records = [dns_ns_record for dns_ns_record in additional_oois if isinstance(dns_ns_record, DNSNSRecord)]
    dns_aaaa_records = [
        dns_aaaa_record for dns_aaaa_record in additional_oois if isinstance(dns_aaaa_record, DNSAAAARecord)
    ]

    if dns_aaaa_records:
        return

    for dns_ns_record in dns_ns_records:
        finding_type = KATFindingType(id="KAT-NAMESERVER-NO-IPV6")
        yield finding_type
        yield Finding(
            finding_type=finding_type.reference,
            ooi=dns_ns_record.reference,
            description="This nameserver has no ipv6 address",
        )
