from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.network import IPPort, IPAddress

BIT = BitDefinition(
    id="port-classification",
    consumes=IPPort,
    parameters=[],
    module="bits.port_classification.port_classification",
)
