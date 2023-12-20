from typing import Dict

from pydantic import BaseModel, Field


class PrioritizedItemRequest(BaseModel):
    """Request model for prioritized items used in the server."""

    priority: int
    data: Dict = Field(default_factory=dict)
