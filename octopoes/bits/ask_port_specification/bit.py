from bits.definitions import BitDefinition
from octopoes.models.ooi.network import Network

BIT = BitDefinition(
    id="ask-port-specification",
    consumes=Network,
    parameters=[],
    min_scan_level=0,
    module="bits.ask_port_specification.ask_port_specification",
)
