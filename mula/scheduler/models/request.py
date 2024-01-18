from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class PrioritizedItemRequest(BaseModel):
    """Request model for prioritized items used in the server."""

    priority: int
    data: Dict = Field(default_factory=dict)


class JobRequest(BaseModel):
    scheduler_id: str

    enabled: bool = True

    p_item: Dict = Field(default_factory=dict)

    cron_expression: Optional[str] = None

    deadline_at: Optional[datetime] = None
