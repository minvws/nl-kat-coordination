from bits.definitions import BitDefinition
from octopoes.models.ooi.network import Network

BIT = BitDefinition(
    id="ask-disallowed-domains",
    consumes=Network,
    parameters=[],
    min_scan_level=0,
    module="bits.ask_disallowed_domains.ask_disallowed_domains",
)
