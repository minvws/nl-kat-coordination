from typing import List, Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.types import NXDOMAIN


def run(
    input_ooi: Hostname,
    additional_oois: List[NXDOMAIN],
) -> Iterator[OOI]:

    if additional_oois:
        nxdomain = KATFindingType(id="KAT-NXDOMAIN")
        yield nxdomain
        yield Finding(
            finding_type=nxdomain.reference,
            ooi=input_ooi.reference,
            description=f"The domain does not exist.",
        )
