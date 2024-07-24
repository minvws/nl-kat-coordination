from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.dns.records import DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname

BIT = BitDefinition(
    id="domain-owner-verification",
    consumes=DNSNSRecord,
    parameters=[BitParameterDefinition(ooi_type=Hostname, relation_path="name_server_hostname")],
    module="bits.domain_owner_verification.domain_owner_verification",
)
