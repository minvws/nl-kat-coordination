from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.ooi.dns.records import DNSTXTRecord

NIBBLE = NibbleDefinition(id="spf-discovery", signature=[NibbleParameter(object_type=DNSTXTRecord)])
