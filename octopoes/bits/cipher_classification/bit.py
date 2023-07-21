from bits.definitions import BitDefinition
from octopoes.models.ooi.service import SSLCipher

BIT = BitDefinition(
    id="cipher-classification",
    consumes=SSLCipher,
    parameters=[],
    module="bits.cipher_classification.cipher_classification",
)
