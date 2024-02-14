from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Scheduler(BaseModel):
    """Representation of a schedulers.Scheduler instance. Used for
    unmarshalling of schedulers to a JSON representation."""

    id: str | None = None
    enabled: bool | None = None
    priority_queue: dict[str, Any] | None = None
    last_activity: datetime | None = None
