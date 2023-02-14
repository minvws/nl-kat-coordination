from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.zone import ResolvedHostname
from octopoes.models.ooi.network import IPAddress
from octopoes.models.ooi.service import IPService

BIT = BitDefinition(
    id="website-discovery",
    consumes=IPAddress,
    parameters=[
        BitParameterDefinition(ooi_type=IPService, relation_path="ip_port.address"),
        BitParameterDefinition(ooi_type=ResolvedHostname, relation_path="address"),
    ],
    module="bits.website_discovery.website_discovery",
)
