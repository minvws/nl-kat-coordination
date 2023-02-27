from bits.definitions import BitDefinition
from octopoes.models.types import RawCookie

BIT = BitDefinition(
    id="cookie_parser",
    consumes=RawCookie,
    parameters=[],
    module="bits.cookie_parser.cookie_parser",
)
