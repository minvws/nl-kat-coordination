from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.dns.records import NXDOMAIN
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DKIMExists

BIT = BitDefinition(
    id="missing-dkim",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=DKIMExists, relation_path="hostname"),
        BitParameterDefinition(ooi_type=NXDOMAIN, relation_path="hostname"),
    ],
    module="bits.missing_dkim.missing_dkim",
)
