import datetime
from typing import Dict, Iterator, List

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.types import HTTPHeader


def run(input_ooi: HTTPHeader, additional_oois: List, config: Dict[str, str]) -> Iterator[OOI]:
    header = input_ooi
    if header.key.lower() != "strict-transport-security":
        return

    one_year = datetime.timedelta(days=365).total_seconds()

    max_age = int(config.get("max-age", one_year)) if config else one_year
    findings: [str] = []

    if "includesubdomains" not in header.value.lower():
        findings.append("The HSTS should include subdomains.")

    if "max-age" not in header.value.lower():
        findings.append("The cache validity period of the HSTS should be defined and should be at least 1 year.")

    if "max-age" in header.value.lower() and int(header.value.split("=")[1].strip('"').split(";")[0]) < max_age:
        findings.append(f"The cache validity period of the HSTS should be at least be {max_age} seconds.")

    if findings:
        description: str = "List of HSTS findings:\n"
        for index, finding in enumerate(findings):
            description += f"\n {index + 1}. {finding}"

        yield from _create_kat_finding(
            header.reference,
            kat_id="KAT-HSTS-VULNERABILITIES",
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
