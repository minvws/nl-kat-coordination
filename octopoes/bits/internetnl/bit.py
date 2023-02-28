from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.web import Website

BIT = BitDefinition(
    id="internet-nl",
    consumes=Hostname,
    parameters=[
        BitParameterDefinition(ooi_type=Finding, relation_path="ooi"),  # findings on hostnames
        BitParameterDefinition(ooi_type=Finding, relation_path="ooi.website.hostname"),  # findings on resources
        BitParameterDefinition(ooi_type=Finding, relation_path="ooi.resource.website.hostname"),  # findings on headers
        BitParameterDefinition(ooi_type=Finding, relation_path="ooi.hostname"),  # findings on websites
        BitParameterDefinition(ooi_type=Finding, relation_path="ooi.netloc"),  # findings on weburls
        BitParameterDefinition(ooi_type=Website, relation_path="hostname"),  # only websites have to comply
    ],
    module="bits.internetnl.internetnl",
)
