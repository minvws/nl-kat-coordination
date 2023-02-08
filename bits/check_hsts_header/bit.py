from bits.definitions import BitDefinition
from octopoes.models.types import HTTPHeader

BIT = BitDefinition(
    id="check-hsts-header",
    consumes=HTTPHeader,
    parameters=[],
    module="bits.check_hsts_header.check_hsts_header",
)
