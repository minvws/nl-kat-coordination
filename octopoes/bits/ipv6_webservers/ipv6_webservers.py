from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord, DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import KATFindingType, Finding


def run(
    hostname: Hostname,
    additional_oois: List[Union[DNSAAAARecord, DNSARecord, DNSNSRecord]],
) -> Iterator[OOI]:

    dns_a_records = [dns_a_record for dns_a_record in additional_oois if isinstance(dns_a_record, DNSARecord)]
    dns_aaaa_records = [
        dns_aaaa_record for dns_aaaa_record in additional_oois if isinstance(dns_aaaa_record, DNSAAAARecord)
    ]
    dns_ns_records = [dns_ns_record for dns_ns_record in additional_oois if isinstance(dns_ns_record, DNSNSRecord)]

    is_nameserver = bool(dns_ns_records)

    if dns_a_records and not dns_aaaa_records and not is_nameserver:
        finding_type = KATFindingType(id="KAT-581")
        yield finding_type
        yield Finding(
            finding_type=finding_type.reference,
            ooi=hostname.reference,
            description="There are no webservers with an IPv6 address.",
        )
