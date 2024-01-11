from datetime import datetime, timezone
from typing import Dict, Optional

from pydantic import BaseModel, Field

from .queue import PrioritizedItem
from .rate_limit import RateLimit


class PrioritizedItemRequest(BaseModel):
    """Request model for prioritized items used in the server."""

    priority: int
    data: Dict = Field(default_factory=dict)


class JobRequest(BaseModel):
    scheduler_id: str

    enabled: bool = True

    p_item: Dict = Field(default_factory=dict)

    # TODO: not yet implemented, added as proof of concept
    rate_limit: Optional[RateLimit] = None

    # TODO: not yet implemented, added as proof of concept
    crontab: Optional[str] = None

    deadline_at: Optional[datetime] = None
