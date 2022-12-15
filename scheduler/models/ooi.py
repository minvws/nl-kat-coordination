from typing import Optional

from pydantic import BaseModel

from .scan_profile import ScanProfile


class OOI(BaseModel):
    """Representation of "Object Of Interests" from Octopoes."""

    primary_key: str
    object_type: str
    scan_profile: ScanProfile
