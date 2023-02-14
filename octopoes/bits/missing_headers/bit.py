from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.web import HTTPResource, HTTPHeader

BIT = BitDefinition(
    id="missing-headers",
    consumes=HTTPResource,
    parameters=[
        BitParameterDefinition(ooi_type=HTTPHeader, relation_path="resource"),
    ],
    module="bits.missing_headers.missing_headers",
)
