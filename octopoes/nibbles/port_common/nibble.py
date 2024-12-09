from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.ooi.network import IPPort

NIBBLE = NibbleDefinition(name="port-common", signature=[NibbleParameter(object_type=IPPort)])
