from bits.definitions import BitParameterDefinition, BitDefinition
from octopoes.models.ooi.web import HTTPResource, WebURL, HTTPHeader, HostnameHTTPURL

BIT = BitDefinition(
    id="https-redirect",
    consumes=HostnameHTTPURL,
    parameters=[
        BitParameterDefinition(ooi_type=HTTPHeader, relation_path="resource.web_url"),
    ],
    module="bits.https_redirect.https_redirect",
)
