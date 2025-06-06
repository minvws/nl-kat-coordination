from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.ooi.dns.records import DNSNSRecord

NIBBLE = NibbleDefinition(id="domain-owner-verification", signature=[NibbleParameter(object_type=DNSNSRecord)])
