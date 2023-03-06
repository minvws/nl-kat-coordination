from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.certificate import X509Certificate
from octopoes.models.ooi.web import Website

BIT = BitDefinition(
    id="expiring-certificate",
    consumes=X509Certificate,
    parameters=[],
    module="bits.expiring_certificate.expiring_certificate",
)
