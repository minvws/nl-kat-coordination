from typing import Any, List, Optional

from pydantic import BaseModel


class ServiceHealth(BaseModel):
    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = []


ServiceHealth.update_forward_refs()
