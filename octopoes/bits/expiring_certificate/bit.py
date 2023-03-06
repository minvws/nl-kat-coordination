from bits.definitions import BitDefinition
from octopoes.models.ooi.certificate import X509Certificate

BIT = BitDefinition(
    id="expiring-certificate",
    consumes=X509Certificate,
    parameters=[],
    module="bits.expiring_certificate.expiring_certificate",
)
