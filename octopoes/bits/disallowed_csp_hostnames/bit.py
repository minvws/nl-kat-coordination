from bits.definitions import BitDefinition
from octopoes.models.ooi.web import HTTPHeaderHostname

BIT = BitDefinition(
    id="disallowed-csp-hostnames",
    consumes=HTTPHeaderHostname,
    parameters=[],
    module="bits.disallowed_csp_hostnames.disallowed_csp_hostnames",
    config_ooi_relation_path="HTTPHeaderHostname.hostname.network",
)
