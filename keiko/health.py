"""Keiko health module"""
from typing import Optional, Any, List

from pydantic import BaseModel

from keiko.version import __version__


class ServiceHealth(BaseModel):
    """KAT Health model"""

    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = []


ServiceHealth.update_forward_refs()


def get_health() -> ServiceHealth:
    """Determine health of Keiko service"""
    return ServiceHealth(
        service="keiko",
        healthy=True,
        version=__version__,
    )
