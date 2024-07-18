from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    response_text = raw.decode()
    pk_ooi = Reference.from_str(input_ooi["primary_key"])

    if '<div class="error blok-onderkant-1" role="alert">' in response_text:
        findingtype = KATFindingType(id="KAT-FRAUDULENT-TRADER")
        yield findingtype
        yield Finding(
            finding_type=findingtype.reference,
            ooi=pk_ooi,
            description="The referenced object is known to be a fraudulent trade partner",
        )

    elif '<div class="success blok-onderkant-1">' not in response_text:
        raise Exception("Fraudulent trader check did not return safe nor fraudulent")
