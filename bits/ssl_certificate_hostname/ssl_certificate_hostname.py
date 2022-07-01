from typing import List, Iterator

from octopoes.models import OOI
from octopoes.models.ooi.certificate import Certificate
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.network import IPPort
from octopoes.models.ooi.web import Website


def run(
    input_ooi: Website,
    additional_oois: List[Certificate],
) -> Iterator[OOI]:

    if not additional_oois:
        return

    # this is temporary since we do not know from the model which of te certs coupled to the website signs the website
    certificate_subjects = [certificate.subject for certificate in additional_oois]
    hostname = input_ooi.hostname.tokenized.name

    hostname = hostname if hostname[-1] != "." else hostname[:-1]

    for subject in certificate_subjects:
        cleaned_subject = subject if subject[-1] != "." else subject[:-1]
        if hostname == cleaned_subject:
            return

    ft = KATFindingType(id="KAT-SSL-CERT-HOSTNAME-MISMATCH")
    yield Finding(
        ooi=input_ooi.reference,
        finding_type=ft.reference,
        description=f"The hostname {hostname} does not match the subject of the certificate",
    )
