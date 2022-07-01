from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.types import NXDOMAIN

BIT = BitDefinition(
    id="nxdomain-flag",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=NXDOMAIN, relation_path="hostname"),
    ],
    module="bits.nxdomain_flag.nxdomain_flag",
)
