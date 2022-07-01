from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.certificate import Certificate
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.service import IPService
from octopoes.models.ooi.web import Website


def run(
    input_ooi: IPService,
    additional_oois: List[Union[Certificate, Website]],
) -> Iterator[OOI]:

    if input_ooi.service.tokenized.name != "https":
        return

    websites_with_certificates = [
        certificate.website for certificate in additional_oois if isinstance(certificate, Certificate)
    ]
    websites = [website.reference for website in additional_oois if isinstance(website, Website)]

    # Check if the website is in the list of websites with certificates
    for website in websites:
        if website not in websites_with_certificates:
            ft = KATFindingType(id="KAT-NO-CERTIFICATE")
            yield ft
            yield Finding(ooi=website, finding_type=ft.reference, description="No SSL certificate found")
