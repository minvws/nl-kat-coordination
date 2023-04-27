import json
from typing import Callable

from scheduler.models import RawDataReceivedEvent

from .listeners import RabbitMQ


class RawData(RabbitMQ):
    def __init__(self, dsn: str, queue: str, func: Callable):
        super().__init__(dsn)
        self.queue = queue
        self.func = func

    def listen(self) -> None:
        self.basic_consume(self.queue, False)

    def dispatch(self, body: bytes) -> None:
        # Convert body into a RawDataReceivedEvent
        body_str = body.decode("utf-8")
        body_dict = json.loads(body_str)
        model = RawDataReceivedEvent(**body_dict)

        # Call the function
        self.func(model)
