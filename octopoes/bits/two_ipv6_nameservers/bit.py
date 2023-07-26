from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.dns.records import DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding

BIT = BitDefinition(
    id="two-ipv6-nameservers",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=Finding, relation_path="ooi [is DNSNSRecord].hostname"),
        BitParameterDefinition(ooi_type=DNSNSRecord, relation_path="hostname"),
    ],
    module="bits.two_ipv6_nameservers.two_ipv6_nameservers",
)
