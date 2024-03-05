from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PrioritizedItemRequest(BaseModel):
    """Request model for prioritized items used in the server."""

    priority: int
    data: dict = Field(default_factory=dict)


class ScheduleRequest(BaseModel):
    scheduler_id: str

    enabled: bool = True

    p_item: dict = Field(default_factory=dict)

    cron_expression: str | None = None

    deadline_at: datetime | None = None
