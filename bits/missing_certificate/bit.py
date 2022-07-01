from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.certificate import Certificate
from octopoes.models.ooi.service import IPService
from octopoes.models.ooi.web import Website

BIT = BitDefinition(
    id="missing-certificate",
    consumes=IPService,
    parameters=[
        BitParameterDefinition(ooi_type=Certificate, relation_path="website.ip_service"),
        BitParameterDefinition(ooi_type=Website, relation_path="ip_service"),
    ],
    module="bits.missing_certificate.missing_certificate",
)
