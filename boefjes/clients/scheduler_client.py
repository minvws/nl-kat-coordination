from typing import Union, List, Optional

import requests
from pydantic import BaseModel, parse_obj_as

from boefjes.job_models import BoefjeMeta, NormalizerMeta


class Queue(BaseModel):
    id: str
    size: int


class Task(BaseModel):
    # This works because Pydantic cannot parse NormalizerMeta data to a BoefjeMeta
    item: Union[BoefjeMeta, NormalizerMeta]


class SchedulerClientInterface:
    def get_queues(self) -> List[Queue]:
        raise NotImplementedError()

    def pop_task(self, queue: str) -> Optional[Task]:
        raise NotImplementedError()


class SchedulerAPIClient(SchedulerClientInterface):
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._session = requests.Session()

    @staticmethod
    def _verify_response(response: requests.Response) -> None:
        response.raise_for_status()

    def get_queues(self) -> List[Queue]:
        response = self._session.get(f"{self.base_url}/queues")
        self._verify_response(response)

        return parse_obj_as(List[Queue], response.json())

    def pop_task(self, queue: str) -> Optional[Task]:
        response = self._session.get(f"{self.base_url}/queues/{queue}/pop")
        self._verify_response(response)

        return parse_obj_as(Optional[Task], response.json())
