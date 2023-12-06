"""Keiko health module."""
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from keiko.version import __version__


class ServiceHealth(BaseModel):
    """KAT Health model."""

    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = Field(default_factory=list)


ServiceHealth.update_forward_refs()


def get_health() -> ServiceHealth:
    """Determine health of Keiko service."""
    return ServiceHealth(
        service="keiko",
        healthy=True,
        version=__version__,
    )
