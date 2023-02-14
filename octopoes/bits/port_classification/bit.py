from bits.definitions import BitDefinition
from octopoes.models.ooi.network import IPPort

BIT = BitDefinition(
    id="port-classification",
    consumes=IPPort,
    parameters=[],
    module="bits.port_classification.port_classification",
)
