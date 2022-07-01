from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.dns.records import DNSARecord, DNSAAAARecord, DNSCNAMERecord
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname

BIT = BitDefinition(
    id="dns-alias-resolving",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=ResolvedHostname, relation_path="hostname"),
        BitParameterDefinition(ooi_type=DNSCNAMERecord, relation_path="target_hostname"),
    ],
    module="bits.dns_alias_resolving.dns_alias_resolving",
)
