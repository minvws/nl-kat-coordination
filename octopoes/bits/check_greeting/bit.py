from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.greeting import Greeting

BIT = BitDefinition(
    id="check-greeting",
    consumes=Greeting,
    parameters=[],
    module="bits.check_greeting.check_greeting",
)
