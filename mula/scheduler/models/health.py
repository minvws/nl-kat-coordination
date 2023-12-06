from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    """ServiceHealth is used as response model for health check in the
    server.Server for the health endpoint.
    """

    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = Field(default_factory=list)
    externals: Dict[str, bool] = {}


ServiceHealth.model_rebuild()
