from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.certificate import (
    X509Certificate,
    SubjectAlternativeNameHostname,
)
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.web import Website


def run(
    input_ooi: X509Certificate,
    additional_oois: List[Union[Website, SubjectAlternativeNameHostname]],
) -> Iterator[OOI]:

    subject = input_ooi.subject.rstrip(".")

    websites = [website for website in additional_oois if isinstance(website, Website)]
    subject_alternative_names = [
        subject_alternative_name.hostname.tokenized.name.rstrip(".")
        for subject_alternative_name in additional_oois
        if isinstance(subject_alternative_name, SubjectAlternativeNameHostname)
    ]

    for website in websites:
        hostname = website.hostname.tokenized.name.rstrip(".")
        if hostname != subject:
            if hostname not in subject_alternative_names:
                ft = KATFindingType(id="KAT-SSL-CERT-HOSTNAME-MISMATCH")
                yield Finding(
                    ooi=website.reference,
                    finding_type=ft.reference,
                    description=f"The hostname {website.hostname} does not match the subject of the certificate",
                )
