from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = Field(default_factory=list)


ServiceHealth.update_forward_refs()
