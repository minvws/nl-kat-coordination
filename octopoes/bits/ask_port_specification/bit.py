from bits.definitions import BitDefinition
from octopoes.models.ooi.network import Network


BIT = BitDefinition(
    id="ask-port-specification",
    consumes=Network,
    parameters=[],
    module="bits.ask_port_specification.ask_port_specification",
)
