from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.web import HTTPHeaderHostname
from octopoes.models.types import NXDOMAIN

BIT = BitDefinition(
    id="nxdomain-header-flag",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=NXDOMAIN, relation_path="hostname"),
        BitParameterDefinition(ooi_type=HTTPHeaderHostname, relation_path="hostname"),
    ],
    module="bits.nxdomain_header_flag.nxdomain_header_flag",
)
