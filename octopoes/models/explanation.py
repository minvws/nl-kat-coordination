from pydantic import BaseModel, ConfigDict

from octopoes.models import Reference, ScanProfileType


class InheritanceSection(BaseModel):
    reference: Reference
    level: int
    segment: str | None = None
    scan_profile_type: ScanProfileType
    model_config = ConfigDict(arbitrary_types_allowed=True)
