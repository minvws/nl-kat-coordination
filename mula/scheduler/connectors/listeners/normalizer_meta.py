from typing import Optional

from scheduler.connectors.errors import exception_handler
from scheduler.models import NormalizerMetaReceivedEvent

from .listeners import RabbitMQ


class NormalizerMeta(RabbitMQ):
    name = "normalizer_meta"

    @exception_handler
    def get_latest_normalizer_meta(self, queue: str) -> Optional[NormalizerMetaReceivedEvent]:
        response = self.get(queue)
        if response is None:
            return None

        return NormalizerMetaReceivedEvent(**response)
