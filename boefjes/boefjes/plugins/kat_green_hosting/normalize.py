from typing import Union, Iterator
import json
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import KATFindingType, Finding

from boefjes.job_models import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
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
