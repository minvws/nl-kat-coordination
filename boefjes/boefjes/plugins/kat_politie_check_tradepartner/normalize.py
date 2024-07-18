from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    pk_ooi = Reference.from_str(input_ooi["primary_key"])

    if "Er zijn meldingen over deze verkoper!" in str(raw):
        findingtype = KATFindingType(id="KAT-FRAUDULENT-TRADER")
        yield findingtype
        yield Finding(
            finding_type=findingtype.reference,
            ooi=pk_ooi,
            description="The referenced object is known to be a fraudulent trade partner",
        )
