from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.dns.zone import ResolvedHostname
from octopoes.models.ooi.network import IPAddress, IPPort

BIT = BitDefinition(
    id="url-discovery",
    consumes=IPAddress,
    parameters=[
        BitParameterDefinition(ooi_type=IPPort, relation_path="address"),
        BitParameterDefinition(ooi_type=ResolvedHostname, relation_path="address"),
    ],
    module="bits.url_discovery.url_discovery",
    min_scan_level=0,
)
