from typing import Callable

from scheduler.models import ScanProfileMutation as ScanProfileMutationModel

from .listeners import RabbitMQ


class ScanProfileMutation(RabbitMQ):
    def __init__(self, dsn: str, queue: str, func: Callable):
        super().__init__(dsn)
        self.queue = queue
        self.func = func

    def listen(self) -> None:
        self.basic_consume(self.queue, True)

    def dispatch(self, body: bytes) -> None:
        # Convert body into a ScanProfileMutationModel
        model = ScanProfileMutationModel.parse_raw(body)

        # Call the function
        self.func(model)
