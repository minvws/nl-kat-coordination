from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DKIMExists

BIT = BitDefinition(
    id="missing-dkim",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=DKIMExists, relation_path="hostname"),
    ],
    module="bits.missing_dkim.missing_dkim",
)
