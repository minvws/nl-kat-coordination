from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.ooi.certificate import X509Certificate

NIBBLE = NibbleDefinition(name="expiring-certificate", signature=[NibbleParameter(object_type=X509Certificate)])
