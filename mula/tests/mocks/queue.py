from scheduler import queues

from tests.utils import functions


class MockPriorityQueue(queues.PriorityQueue):
    def create_hash(self, item: functions.TestModel):
        return item.id.hex
