from pydantic import BaseModel, Field


class PrioritizedItem(BaseModel):
    """Request model for prioritized items used in the server."""

    priority: int
    data: dict = Field(default_factory=dict)
