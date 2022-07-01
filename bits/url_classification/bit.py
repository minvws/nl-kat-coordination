from bits.definitions import BitDefinition
from octopoes.models.ooi.web import WebURL, URL

BIT = BitDefinition(
    id="url-classification",
    consumes=URL,
    parameters=[],
    module="bits.url_classification.url_classification",
)
