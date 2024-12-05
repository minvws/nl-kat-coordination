from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.ooi.dns.records import DNSTXTRecord

NIBBLE = NibbleDefinition(name="spf-discovery", signature=[NibbleParameter(object_type=DNSTXTRecord)])
