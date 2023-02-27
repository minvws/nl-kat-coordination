from bits.definitions import BitDefinition
from octopoes.models.types import HTTPHeader

BIT = BitDefinition(
    id="cookies_from_headers",
    consumes=HTTPHeader,
    parameters=[],
    module="bits.cookies_from_headers.cookies_from_headers",
)
