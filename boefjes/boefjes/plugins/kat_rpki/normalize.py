import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    results = json.loads(raw)
    ooi = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

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
