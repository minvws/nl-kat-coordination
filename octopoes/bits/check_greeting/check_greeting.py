from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.greeting import Greeting

def run(
    input_ooi: Greeting,
    additional_oois: list,
    config: dict,
) -> Iterator[OOI]:
    greeting_text = input_ooi.greeting
    address = input_ooi.address

    kat = KATFindingType(id="KAT-GREETING")
    yield kat
    yield Finding(
        finding_type=kat.reference,
        ooi=input_ooi.reference,
        description=f"We have received a greeting: {greeting_text} because of address: {str(address)}.",
    )