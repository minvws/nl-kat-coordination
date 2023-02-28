from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.network import IPAddress, IPPort
from octopoes.models.ooi.web import Website

BIT = BitDefinition(
    id="https-availability",
    consumes=IPAddress,
    parameters=[
        BitParameterDefinition(ooi_type=IPPort, relation_path="address"),
        BitParameterDefinition(
            ooi_type=Website, relation_path="ip_service.ip_port.address"
        ),  # we place the findings on the http websites
    ],
    module="bits.https_availability.https_availability",
)
