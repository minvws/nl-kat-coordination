import json
from typing import Union, Iterator

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import KATFindingType, Finding

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    result = json.loads(raw)

    reference = Reference.from_str(normalizer_meta.boefje_meta.input_ooi)

    if "website_similarity" in result and result["website_similarity"] < 0.9:
        ft = KATFindingType(id="KAT-585")
        finding = Finding(
            finding_type=ft.reference,
            ooi=reference,
            description=f"The websites hosted on IPv4 and IPv6 are not the same.",
        )
        yield ft
        yield finding
