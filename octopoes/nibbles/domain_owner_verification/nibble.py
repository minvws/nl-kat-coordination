from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.ooi.dns.records import DNSNSRecord

NIBBLE = NibbleDefinition(name="domain-owner-verification", signature=[NibbleParameter(object_type=DNSNSRecord)])
