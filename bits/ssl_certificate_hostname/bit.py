from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.certificate import Certificate
from octopoes.models.ooi.web import Website

BIT = BitDefinition(
    id="ssl-certificate-hostname",
    consumes=Website,
    parameters=[
        BitParameterDefinition(ooi_type=Certificate, relation_path="website"),
    ],
    module="bits.ssl_certificate_hostname.ssl_certificate_hostname",
)
