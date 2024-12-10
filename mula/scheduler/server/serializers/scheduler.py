from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Scheduler(BaseModel):
    id: str
    type: str
    item_type: str
    qsize: int = 0
    last_activity: datetime | None = None
