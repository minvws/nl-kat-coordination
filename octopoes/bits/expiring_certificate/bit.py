from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.certificate import X509Certificate
from octopoes.models.ooi.web import Website

BIT = BitDefinition(
    id="expiring-certificate",
    consumes=X509Certificate,
    parameters=[
        BitParameterDefinition(ooi_type=Website, relation_path="certificate"),
    ],
    module="bits.expiring_certificate.expiring_certificate",
)
