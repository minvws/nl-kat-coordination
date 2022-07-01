from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.dns.records import DNSARecord, DNSAAAARecord, DNSCNAMERecord
from octopoes.models.ooi.dns.zone import Hostname

BIT = BitDefinition(
    id="dns-resolving",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=DNSARecord, relation_path="hostname"),
        BitParameterDefinition(ooi_type=DNSAAAARecord, relation_path="hostname"),
    ],
    module="bits.dns_resolving.dns_resolving",
)
