from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.web import Website, SecurityTXT

BIT = BitDefinition(
    id="missing_security_txt",
    consumes=Website,
    parameters=[
        BitParameterDefinition(ooi_type=SecurityTXT, relation_path="website"),
    ],
    module="bits.missing_security_txt.missing_security_txt",
)
