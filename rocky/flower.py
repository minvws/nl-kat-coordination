import logging
from enum import Enum
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


class State(Enum):
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"


class FlowerException(Exception):
    ...


class FlowerClient:
    def __init__(self, base_uri: str):
        self._base_uri = base_uri

    def get_tasks(
        self,
        task_name: Optional[str] = None,
        limit: int = 0,
        state: Optional[State] = None,
    ) -> Dict[str, Dict[str, Any]]:
        params = {}
        if task_name:
            params["taskname"] = task_name
        if limit:
            params["limit"] = str(limit)
        if state:
            params["state"] = state.value

        try:
            res = requests.get(f"{self._base_uri}/api/tasks", params)
            res.raise_for_status()

            return res.json()
        except Exception as ex:
            raise FlowerException("API request to Flower failed.") from ex
