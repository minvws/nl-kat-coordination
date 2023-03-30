from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DMARCTXTRecord

BIT = BitDefinition(
    id="missing-dmarc",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=DMARCTXTRecord, relation_path="hostname"),
    ],
    module="bits.missing_dmarc.missing_dmarc",
)
