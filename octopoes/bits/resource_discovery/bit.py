from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.web import HostnameHTTPURL, Website

BIT = BitDefinition(
    id="resource-discovery",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=HostnameHTTPURL, relation_path="netloc"),
        BitParameterDefinition(ooi_type=Website, relation_path="hostname"),
    ],
    module="bits.resource_discovery.resource_discovery",
)
