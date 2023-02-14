from typing import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.web import Website


def run(
    input_ooi: Website,
    additional_oois,
) -> Iterator[OOI]:

    if input_ooi.ip_service.tokenized.service.name.lower() != "https":
        return

    if input_ooi.certificate is None:
        ft = KATFindingType(id="KAT-NO-CERTIFICATE")
        yield ft
        yield Finding(ooi=input_ooi.reference, finding_type=ft.reference, description="No SSL certificate found")
