import json
from typing import Union, Iterator

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import KATFindingType, Finding

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    result = json.loads(raw)

    boefje_meta = normalizer_meta.boefje_meta
    pk = boefje_meta.input_ooi
    ooi_ref = Reference.from_str(pk)

    possible_errors: [str] = [
        "Bogus DNSSEC signature",
        "DNSSEC signature not incepted yet",
        "Unknown cryptographic algorithm",
        "DNSSEC signature has expired",
    ]

    if (
        "No trusted keys found in tree" in result
        and "No DNSSEC public key(s)" in result
    ):
        ft = KATFindingType(id="KAT-600")
        finding = Finding(
            finding_type=ft.reference,
            ooi=ooi_ref,
            description=f"Domain {ooi_ref.human_readable} is not signed with DNSSEC.",
        )
        yield ft
        yield finding

    if "No trusted keys found in tree" in result and [
        error for error in possible_errors if error in result
    ]:
        ft = KATFindingType(id="KAT-601")
        finding = Finding(
            finding_type=ft.reference,
            ooi=ooi_ref,
            description=f"Domain {ooi_ref.human_readable} is signed with an invalid DNSSEC.",
        )
        yield ft
        yield finding
