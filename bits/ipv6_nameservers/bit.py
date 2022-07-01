from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord, DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname

BIT = BitDefinition(
    id="ipv6-on-nameservers",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=DNSNSRecord, relation_path="name_server_hostname"),
        BitParameterDefinition(ooi_type=DNSAAAARecord, relation_path="hostname"),
    ],
    module="bits.ipv6_nameservers.ipv6_nameservers",
)
