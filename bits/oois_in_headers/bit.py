from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.types import HTTPHeader

BIT = BitDefinition(
    id="oois-in-headers",
    consumes=HTTPHeader,
    parameters=[],
    module="bits.oois_in_headers.oois_in_headers",
)
