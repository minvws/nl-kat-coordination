import datetime
from typing import List, Iterator

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.types import HTTPHeader


def run(
    input_ooi: HTTPHeader,
    additional_oois: List,
) -> Iterator[OOI]:

    header = input_ooi
    if header.key.lower() != "strict-transport-security":
        return

    one_year = datetime.timedelta(days=365).total_seconds()
    findings: [str] = []

    if "includeSubDomains" not in header.value:
        findings.append("The HSTS should include subdomains.")

    if "max-age" not in header.value:
        findings.append("The cache validity period of the HSTS should be defined and should be at least 1 year.")

    if "max-age" in header.value and int(header.value.split("=")[1].split(";")[0]) < one_year:
        findings.append("The cache validity period of the HSTS should be at least 1 year.")

    if findings:
        description: str = "List of HSTS findings:\n"
        for index, finding in enumerate(findings):
            description += f"\n {index + 1}. {finding}"

        yield from _create_kat_finding(
            header.reference,
            kat_id="KAT-606",
            description=description,
        )


def _create_kat_finding(header: Reference, kat_id: str, description: str) -> Iterator[OOI]:
    finding_type = KATFindingType(id=kat_id)
    yield finding_type
    yield Finding(
        finding_type=finding_type.reference,
        ooi=header,
        description=description,
    )
