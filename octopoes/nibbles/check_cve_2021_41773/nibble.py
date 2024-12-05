from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.types import HTTPHeader

NIBBLE = NibbleDefinition(name="check_cve_2021_41773", signature=[NibbleParameter(object_type=HTTPHeader)])
