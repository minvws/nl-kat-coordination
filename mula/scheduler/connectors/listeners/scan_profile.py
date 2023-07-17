from typing import Callable

from scheduler.models import ScanProfileMutation as ScanProfileMutationModel

from .listeners import RabbitMQ


class ScanProfileMutation(RabbitMQ):
    def __init__(self, dsn: str, queue: str, func: Callable, prefetch_count: int):
        super().__init__(dsn)
        self.queue = queue
        self.func = func
        self.prefetch_count = prefetch_count

    def listen(self) -> None:
        self.basic_consume(self.queue, True, self.prefetch_count)

    def dispatch(self, body: bytes) -> None:
        # Convert body into a ScanProfileMutationModel
        model = ScanProfileMutationModel.parse_raw(body)

        # Call the function
        self.func(model)
