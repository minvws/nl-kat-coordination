"""Keiko health module."""
from typing import Any

from pydantic import BaseModel, Field

from keiko.version import __version__


class ServiceHealth(BaseModel):
    """KAT Health model."""

    service: str
    healthy: bool = False
    version: str | None = None
    additional: Any = None
    results: list["ServiceHealth"] = Field(default_factory=list)


ServiceHealth.update_forward_refs()


def get_health() -> ServiceHealth:
    """Determine health of Keiko service."""
    return ServiceHealth(
        service="keiko",
        healthy=True,
        version=__version__,
    )
