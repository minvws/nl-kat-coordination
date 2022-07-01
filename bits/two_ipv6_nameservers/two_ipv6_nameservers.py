from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord, DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import KATFindingType, Finding


def run(
    hostname: Hostname,
    additional_oois: List[Union[Finding, DNSNSRecord]],
) -> Iterator[OOI]:

    no_ipv6_findings = [
        finding
        for finding in additional_oois
        if isinstance(finding, Finding) and finding.finding_type.tokenized.id == "KAT-NAMESERVER-NO-IPV6"
    ]

    dns_ns_records = [dns_ns_record for dns_ns_record in additional_oois if isinstance(dns_ns_record, DNSNSRecord)]

    if len(dns_ns_records) - len(no_ipv6_findings) < 2 and dns_ns_records:
        finding_type = KATFindingType(id="KAT-NAMESERVER-NO-TWO-IPV6")
        yield finding_type
        yield Finding(
            finding_type=finding_type.reference,
            ooi=hostname.reference,
            description="This hostname has less than two nameservers with an IPv6 address.",
        )
