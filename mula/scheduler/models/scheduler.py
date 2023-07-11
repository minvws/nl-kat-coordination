from typing import Any, Dict, Optional

from pydantic import BaseModel


class Scheduler(BaseModel):
    """Representation of a schedulers.Scheduler instance. Used for
    unmarshalling of schedulers to a JSON representation."""

    id: Optional[str]
    populate_queue_enabled: Optional[bool]
    priority_queue: Optional[Dict[str, Any]]
