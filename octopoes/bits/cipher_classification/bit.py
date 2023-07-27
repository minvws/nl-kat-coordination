from bits.definitions import BitDefinition
from octopoes.models.ooi.service import TLSCipher

BIT = BitDefinition(
    id="cipher-classification",
    consumes=TLSCipher,
    parameters=[],
    module="bits.cipher_classification.cipher_classification",
)
