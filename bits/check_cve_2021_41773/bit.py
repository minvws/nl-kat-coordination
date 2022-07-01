from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.types import HTTPHeader

BIT = BitDefinition(
    id="check_cve_2021_41773",
    consumes=HTTPHeader,
    parameters=[],
    module="bits.check_cve_2021_41773.check_cve_2021_41773",
)
