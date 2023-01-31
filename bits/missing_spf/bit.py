from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DNSSPFRecord

BIT = BitDefinition(
    id="missing-spf",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=DNSSPFRecord, relation_path="dns_txt_record.hostname"),
    ],
    module="bits.missing_spf.missing_spf",
)
