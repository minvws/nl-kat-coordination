from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.types import HTTPHeader

BIT = BitDefinition(
    id="check-csp-header",
    consumes=HTTPHeader,
    parameters=[],
    module="bits.check_csp_header.check_csp_header",
)
