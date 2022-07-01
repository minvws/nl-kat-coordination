from typing import Optional

from scheduler.connectors.errors import exception_handler
from scheduler.models import RawData as RawDataModel
from scheduler.models import RawDataReceivedEvent

from .listeners import RabbitMQ


class RawData(RabbitMQ):
    name = "raw_data"

    @exception_handler
    def get_latest_raw_data(self, queue: str) -> Optional[RawDataModel]:
        response = self.get(queue)
        if response is None:
            return None

        event = RawDataReceivedEvent(**response)

        return event.raw_data
