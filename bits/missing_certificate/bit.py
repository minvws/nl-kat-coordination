from bits.definitions import BitDefinition
from octopoes.models.ooi.web import Website

BIT = BitDefinition(
    id="missing-certificate",
    consumes=Website,
    parameters=[],
    module="bits.missing_certificate.missing_certificate",
)
