from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.dns.records import DNSNSRecord

BIT = BitDefinition(
    id="domain-owner-verification",
    consumes=DNSNSRecord,
    parameters=[BitParameterDefinition(ooi_type=DNSNSRecord, relation_path="name_server_hostname")],
    module="bits.domain_owner_verification.domain_owner_verification",
)
