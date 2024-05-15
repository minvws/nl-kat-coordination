import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    results = json.loads(raw)
    ooi = Reference.from_str(input_ooi["primary_key"])

    if not results["exists"]:
        ft = KATFindingType(id="KAT-NO-RPKI")
        f = Finding(finding_type=ft.reference, ooi=ooi)
        yield ft
        yield f

    if not results.get("valid") and not results.get("notexpired"):
        ft = KATFindingType(id="KAT-EXPIRED-RPKI")
        f = Finding(finding_type=ft.reference, ooi=ooi)
        yield ft
        yield f
