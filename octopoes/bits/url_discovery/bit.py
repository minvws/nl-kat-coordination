from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.zone import ResolvedHostname
from octopoes.models.ooi.network import IPPort, IPAddress

BIT = BitDefinition(
    id="url-discovery",
    consumes=IPAddress,
    parameters=[
        BitParameterDefinition(ooi_type=IPPort, relation_path="address"),
        BitParameterDefinition(ooi_type=ResolvedHostname, relation_path="address"),
    ],
    module="bits.url_discovery.url_discovery",
)
