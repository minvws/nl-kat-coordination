from bits.definitions import BitDefinition

from octopoes.models.ooi.web import URL

BIT = BitDefinition(
    id="url-classification-mock",
    consumes=URL,
    parameters=[],
    module="bits.url_classification_mock.url_classification_mock",
    min_scan_level=0,
)
