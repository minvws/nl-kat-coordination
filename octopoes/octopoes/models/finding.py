from pydantic import BaseModel

from octopoes.models import OOI
from octopoes.models.ooi.findings import FindingType, Finding


class HydratedFinding(BaseModel):
    finding_type: FindingType
    ooi: OOI
    finding: Finding
