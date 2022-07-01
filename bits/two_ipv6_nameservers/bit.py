from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord, DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding

BIT = BitDefinition(
    id="two-ipv6-nameservers",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=Finding, relation_path="ooi.hostname"),
        BitParameterDefinition(ooi_type=DNSNSRecord, relation_path="hostname"),
    ],
    module="bits.two_ipv6_nameservers.two_ipv6_nameservers",
)
