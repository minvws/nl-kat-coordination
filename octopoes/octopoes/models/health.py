"""Health models for the server."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ServiceHealth(BaseModel):
    """KAT response model for health check endpoint."""

    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = []
    externals: Dict[str, bool] = {}


ServiceHealth.update_forward_refs()
