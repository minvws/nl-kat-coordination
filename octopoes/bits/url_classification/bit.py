from bits.definitions import BitDefinition
from octopoes.models.ooi.web import URL

BIT = BitDefinition(
    id="url-classification",
    consumes=URL,
    parameters=[],
    module="bits.url_classification.url_classification",
)
