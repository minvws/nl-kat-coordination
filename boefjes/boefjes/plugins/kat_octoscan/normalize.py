import json
from collections.abc import Iterable
from typing import Any

from boefjes.normalizer_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def scan_octoscan_output(data: list[dict[str, Any]], ooi_ref: Reference) -> Iterable[NormalizerOutput]:
    for vuln in data:
        finding_type = KATFindingType(id="KAT-VULNERABLE-GH-WORKFLOW")
        yield finding_type
        yield Finding(
            finding_type=finding_type.reference,
            ooi=ooi_ref,
            description=f"Workflow inside {vuln['filepath']} on line {vuln['line']} "
            f"is potentially vulnerable: {vuln['message']}\n"
            f"Snippet: \n {vuln['snippet']}\n",
        )


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    data = json.loads(raw)

    ooi_ref = Reference.from_str(input_ooi["primary_key"])

    yield from scan_octoscan_output(data, ooi_ref)
