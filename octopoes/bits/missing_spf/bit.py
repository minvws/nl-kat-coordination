from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.dns.records import NXDOMAIN
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DNSSPFRecord

BIT = BitDefinition(
    id="missing-spf",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=DNSSPFRecord, relation_path="dns_txt_record.hostname"),
        BitParameterDefinition(ooi_type=NXDOMAIN, relation_path="hostname"),
    ],
    module="bits.missing_spf.missing_spf",
)
