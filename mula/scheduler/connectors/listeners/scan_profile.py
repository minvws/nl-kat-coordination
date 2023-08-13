from typing import Callable

from scheduler.models import ScanProfileMutation as ScanProfileMutationModel

from .listeners import RabbitMQ


class ScanProfileMutation(RabbitMQ):
    """The ScanProfileMutation listener class that listens to the scan profile
    mutation queue and calls the function passed to it. This is used within the
    BoefjeScheduler.

    Attributes:
        queue: A string representing the messaging queue name.
        func: A python callable.
        prefetch_count: An integer representing the prefetch count.
    """

    def __init__(self, dsn: str, queue: str, func: Callable, prefetch_count: int):
        """Initialize the RawData listener.

        Args:
            dsn: A string representing the DSN.
            queue: A string representing the messaging queue name.
            func: A python callable.
            prefetch_count: An integer representing the prefetch count.
        """
        super().__init__(dsn)
        self.queue = queue
        self.func = func
        self.prefetch_count = prefetch_count

    def listen(self) -> None:
        """Listen to the messaging queue."""
        self.basic_consume(self.queue, True, self.prefetch_count)

    def dispatch(self, body: bytes) -> None:
        """Dispatch the message to the function.

        body: A bytes object representing the body of the message.
        """
        # Convert body into a ScanProfileMutationModel
        model = ScanProfileMutationModel.parse_raw(body)

        # Call the function
        self.func(model)
