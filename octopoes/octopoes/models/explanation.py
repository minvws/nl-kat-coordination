from typing import Optional

from pydantic import BaseModel

from octopoes.models import Reference, ScanProfileType


class InheritanceSection(BaseModel):
    reference: Reference
    level: int
    segment: Optional[str]
    scan_profile_type: ScanProfileType

    class Config:
        arbitrary_types_allowed = True
