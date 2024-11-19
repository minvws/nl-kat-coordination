from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Scheduler(BaseModel):
    id: str
    enabled: bool | None = None
    priority_queue: dict[str, Any] | None = None
    last_activity: datetime | None = None
