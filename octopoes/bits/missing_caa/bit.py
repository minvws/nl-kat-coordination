from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.dns.records import NXDOMAIN, DNSCAARecord
from octopoes.models.ooi.dns.zone import Hostname

BIT = BitDefinition(
    id="missing-caa",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=DNSCAARecord, relation_path="dns_caa_record.hostname"),
        BitParameterDefinition(ooi_type=NXDOMAIN, relation_path="hostname"),
    ],
    module="bits.missing_caa.missing_caa",
)
