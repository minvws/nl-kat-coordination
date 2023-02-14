from bytes.events.events import Event


class EventManager:
    def publish(self, event: Event) -> None:
        raise NotImplementedError()
