import time
import unittest
import uuid

import pydantic
from scheduler import dispatchers, queues


def create_p_item(priority: int):
    return queues.PrioritizedItem(
        priority=priority,
        item=TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex),
    )


class TestModel(pydantic.BaseModel):
    id: str
    name: str

    def __hash__(self):
        return hash((self.id, self.name))


class TestDispatcher(dispatchers.Dispatcher):
    pass


class DispatcherTestCase(unittest.TestCase):
    def setUp(self):
        self.pq = queues.PriorityQueue(
            pq_id="test",
            maxsize=10,
            item_type=TestModel,
        )
        self.pq.entry_finder = {}

        self.dispatcher = TestDispatcher(
            pq=self.pq,
            item_type=TestModel,
        )
        self.dispatcher.threshold = float("inf")

    def tearDown(self):
        del self.pq.entry_finder
        del self.pq
        del self.dispatcher

    def test_dispatch_threshold(self):
        """When threshold is set it should only dispatch the items at that
        threshold"""
        self.dispatcher.threshold = 1

        prio1 = create_p_item(priority=1)
        self.pq.push(p_item=prio1)

        prio2 = create_p_item(priority=2)
        self.pq.push(p_item=prio2)

        prio3 = create_p_item(priority=3)
        self.pq.push(p_item=prio3)

        self.assertEqual(3, len(self.pq))

        # Dispatch item on the queue
        self.dispatcher.run()
        self.assertEqual(2, len(self.pq))

        # Check the queue for the correct items
        first_entry = self.pq.peek(0)
        last_entry = self.pq.peek(-1)

        # First item should be the prio2 item
        self.assertEqual(2, first_entry.priority)
        self.assertEqual(prio2, first_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, first_entry.state)

        # Last item should be the prio3 item
        self.assertEqual(3, last_entry.priority)
        self.assertEqual(prio3, last_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, last_entry.state)

        # Dispatch a second time, should have no effect on the queue
        self.dispatcher.run()
        self.assertEqual(2, len(self.pq))

    def test_threshold_not_set(self):
        """When threshold is not set it should dispatch all"""
        prio1 = create_p_item(priority=1)
        self.pq.push(p_item=prio1)

        prio2 = create_p_item(priority=500)
        self.pq.push(p_item=prio2)

        prio3 = create_p_item(priority=1000)
        self.pq.push(p_item=prio3)

        self.assertEqual(3, len(self.pq))

        self.dispatcher.run()
        self.dispatcher.run()
        self.dispatcher.run()

        self.assertEqual(0, len(self.pq))

    def test_threshold_set_to_zero(self):
        """When threshold is set to zero it should not dispatch any"""
        self.dispatcher.threshold = 0

        prio1 = create_p_item(priority=1)
        self.pq.push(p_item=prio1)

        prio2 = create_p_item(priority=500)
        self.pq.push(p_item=prio2)

        prio3 = create_p_item(priority=1000)
        self.pq.push(p_item=prio3)

        self.assertEqual(3, len(self.pq))

        self.dispatcher.run()
        self.dispatcher.run()
        self.dispatcher.run()

        self.assertEqual(3, len(self.pq))

    def test_threshold_with_time(self):
        """When threshold is set to a time it should only dispatch items
        that have been in the queue for that time"""
        self.dispatcher.threshold = time.time()

        prio1 = create_p_item(priority=time.time() - 20)
        self.pq.push(p_item=prio1)

        prio2 = create_p_item(priority=time.time())
        self.pq.push(p_item=prio2)

        prio3 = create_p_item(priority=time.time() + 20)
        self.pq.push(p_item=prio3)

        self.assertEqual(3, len(self.pq))

        # Dispatch item on the queue
        self.dispatcher.run()
        self.assertEqual(2, len(self.pq))

        # Check the queue for the correct items
        first_entry = self.pq.peek(0)
        last_entry = self.pq.peek(-1)

        # First item should be the prio2 item
        self.assertEqual(prio2.priority, first_entry.priority)
        self.assertEqual(prio2, first_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, first_entry.state)

        # Last item should be the prio3 item
        self.assertEqual(prio3.priority, last_entry.priority)
        self.assertEqual(prio3, last_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, last_entry.state)

        # Dispatch a second time, should have no effect on the queue
        self.dispatcher.run()
        self.assertEqual(2, len(self.pq))
