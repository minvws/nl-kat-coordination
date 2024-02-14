import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    data = json.loads(raw.decode())

    pk = boefje_meta.input_ooi
    website_reference = Reference.from_str(pk)

    if not data["green"]:
        ft = KATFindingType(id="KAT-NO-GREEN-HOSTING")
        yield ft
        yield Finding(
            finding_type=ft.reference,
            ooi=website_reference,
            description="This server is not running in a 'green' datacenter according to the Green Web Foundation.",
        )
