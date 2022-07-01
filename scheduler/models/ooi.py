from typing import Optional

from pydantic import BaseModel

from .scan_profile import ScanProfile


class OOI(BaseModel):
    """Representation of "Object Of Interests" from Octopoes."""

    primary_key: str
    name: Optional[str]
    ooi_type: Optional[str]
    object_type: Optional[str]
    scan_profile: ScanProfile
