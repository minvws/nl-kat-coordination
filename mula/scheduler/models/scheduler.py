from typing import Any, Dict, Optional

from pydantic import BaseModel


class Scheduler(BaseModel):
    """Representation of a schedulers.Scheduler instance. Used for
    unmarshalling of schedulers to a JSON representation."""

    id: Optional[str] = None
    enabled: Optional[bool] = None
    priority_queue: Optional[Dict[str, Any]] = None
