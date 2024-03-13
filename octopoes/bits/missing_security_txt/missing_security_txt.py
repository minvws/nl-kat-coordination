from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.web import Website, SecurityTXT


def run(input_ooi: Website, additional_oois: list[SecurityTXT], config: dict[str, str]) -> Iterator[OOI]:
    if not additional_oois:
        ft = KATFindingType(id="KAT-NO-SECURITY-TXT")
        yield ft
        yield Finding(
            ooi=input_ooi.reference,
            finding_type=ft.reference,
            description="This website does not have a Security.txt file",
        )
