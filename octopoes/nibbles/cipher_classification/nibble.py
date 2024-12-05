from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.ooi.service import TLSCipher

NIBBLE = NibbleDefinition(name="cipher-classification", signature=[NibbleParameter(object_type=TLSCipher)])
