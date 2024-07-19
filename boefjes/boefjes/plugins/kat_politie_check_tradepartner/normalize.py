from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


class OutdatedPolitieCheck(Exception):
    pass


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    response_text = raw.decode()
    pk_ooi = Reference.from_str(input_ooi["primary_key"])

    # Check if the website has been marked fraudulent
    if '<div class="error blok-onderkant-1" role="alert">' in response_text:
        findingtype = KATFindingType(id="KAT-FRAUDULENT-TRADER")
        yield findingtype
        yield Finding(
            finding_type=findingtype.reference,
            ooi=pk_ooi,
            description="The referenced object is known to be a fraudulent trade partner",
        )

    elif '<div class="success blok-onderkant-1">' not in response_text:
        # If the website is not marked as fraudulent it is supposed to be marked innocent.
        # If the website is neither, raise Exception since this boefje probably does not work anymore then
        raise OutdatedPolitieCheck("Fraudulent trader check did not return safe nor fraudulent")
