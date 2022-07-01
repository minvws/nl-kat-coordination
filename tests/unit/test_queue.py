import copy
import queue as _queue
import unittest
import uuid

import pydantic
from scheduler import models, queues


def create_p_item(priority: int) -> queues.PrioritizedItem:
    return queues.PrioritizedItem(
        priority=priority,
        item=TestModel(
            id=uuid.uuid4().hex,
            name=uuid.uuid4().hex,
        ),
    )


class TestModel(pydantic.BaseModel):
    id: str
    name: str

    def __hash__(self):
        return hash((self.id, self.name))


class TestPriorityQueue(queues.PriorityQueue):
    def get_item_identifier(self, item: TestModel):
        return item.id


class PriorityQueueTestCase(unittest.TestCase):
    def setUp(self):
        self.pq = TestPriorityQueue(
            pq_id="test-queue",
            maxsize=10,
            item_type=TestModel,
        )
        self.pq.entry_finder = {}

        self._check_queue_empty()

    def tearDown(self):
        del self.pq.entry_finder
        del self.pq

    def _check_queue_empty(self):
        self.assertEqual(0, len(self.pq))
        self.assertEqual(0, len(self.pq.entry_finder))

    def test_push(self):
        """When adding an item to the priority queue, the item should be
        added"""
        item = create_p_item(priority=1)
        self.pq.push(p_item=item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

    def test_push_incorrect_p_item_type(self):
        """When pushing an item that is not of the correct type, the item
        shouldn't be pushed.
        """
        item = {"priority": 1, "item": TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex)}
        p_item = models.QueuePrioritizedItem(**item)

        with self.assertRaises(queues.errors.InvalidPrioritizedItemError):
            self.pq.push(p_item=p_item)

        self.assertEqual(0, len(self.pq))
        self.assertEqual(0, len(self.pq.entry_finder))

    def test_push_replace_not_allowed(self):
        """When pushing an item that is already in the queue the item
        shouldn't be pushed.
        """
        # Set queue to not allow duplicates
        self.pq.allow_replace = False

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        # Add the same item again
        with self.assertRaises(queues.errors.NotAllowedError):
            self.pq.push(p_item=initial_item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

    def test_push_replace_allowed(self):
        """When pushing an item that is already in the queue, but the queue
        allows duplicates, the item should be pushed.
        """
        # Set queue to allow duplicates
        self.pq.allow_replace = True

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        # Add the same item again
        self.pq.push(p_item=initial_item)

        self.assertEqual(2, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        # Check if the item on the queue is the replaced item
        self.assertEqual(initial_item.item.id, self.pq.peek(0).p_item.item.id)

    def test_push_updates_not_allowed(self):
        """When pushing an item that is already in the queue, and the item is
        updated, the item shouldn't be pushed.
        """
        # Set queue to not allow updates
        self.pq.allow_updates = False

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.item.name = "updated-name"

        # Add the same item again
        with self.assertRaises(queues.errors.NotAllowedError):
            self.pq.push(p_item=updated_item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

    def test_push_updates_allowed(self):
        """When pushing an item that is already in the queue, and the item is
        updated, but the queue allows item updates, the item should be pushed.
        """
        # Set queue to allow updates
        self.pq.allow_updates = True

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.item.name = "updated-name"

        # Add the same item again
        self.pq.push(p_item=updated_item)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(2, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        first_entry = self.pq.peek(0)
        last_entry = self.pq.peek(-1)

        # The item with the highest priority should be the one that was added
        # first, with its entry state set to REMOVED
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(initial_item, first_entry.p_item)
        self.assertEqual(queues.EntryState.REMOVED, first_entry.state)

        # Last item should be the updated item
        self.assertEqual(1, last_entry.priority)
        self.assertEqual(updated_item, last_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, last_entry.state)

    def test_push_priority_updates_not_allowed(self):
        """When pushing an item that is already in the queue, and the item
        priority is updated, the item shouldn't be pushed.
        """
        # Set queue to disallow priority updates
        self.pq.allow_priority_updates = False

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 100

        # Add the same item again
        with self.assertRaises(queues.errors.NotAllowedError):
            self.pq.push(p_item=updated_item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

    def test_push_priority_updates_allowed(self):
        """When pushing an item that is already in the queue, and the item
        priority is updated, the item should be pushed.
        """
        # Set queue to allow priority updates
        self.pq.allow_priority_updates = True

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 100

        # Add the same item again
        self.pq.push(p_item=updated_item)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(2, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        first_entry = self.pq.peek(0)
        last_entry = self.pq.peek(-1)

        # The item with the highest priority should be the one that was added
        # first, with its entry state set to REMOVED
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(initial_item, first_entry.p_item)
        self.assertEqual(queues.EntryState.REMOVED, first_entry.state)

        # Last item should be the updated item
        self.assertEqual(100, last_entry.priority)
        self.assertEqual(updated_item, last_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, last_entry.state)

    def test_update_priority_higher(self):
        """When updating the priority of the initial item on the priority queue
        to a higher priority, the updated item should be added to the queue,
        the initial item should be marked as removed, and the initial removed
        from the entry_finder.
        """
        # Set queue to allow updates
        self.pq.allow_priority_updates = True

        # Add an item to the queue
        initial_item = create_p_item(priority=2)
        self.pq.push(p_item=initial_item)

        # Update priority of the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 1
        self.pq.push(p_item=updated_item)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(2, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        first_entry = self.pq.peek(0)
        last_entry = self.pq.peek(-1)

        # Last item should be an item with, EntryState.REMOVED
        self.assertEqual(2, last_entry.priority)
        self.assertEqual(initial_item, last_entry.p_item)
        self.assertEqual(queues.EntryState.REMOVED, last_entry.state)

        # First item should be the updated item, EntryState.ADDED
        self.assertEqual(1, first_entry.priority, 1)
        self.assertEqual(updated_item, first_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, first_entry.state)

        # Item in entry_finder should be the updated item
        item = self.pq.entry_finder[self.pq.get_item_identifier(updated_item.item)]
        self.assertEqual(updated_item.priority, item.priority)
        self.assertEqual(updated_item, item.p_item)
        self.assertEqual(queues.EntryState.ADDED, item.state)

        # When popping off the queue you should end up with the updated_item
        # that now has the highest priority.
        popped_item = self.pq.pop()
        self.assertEqual(updated_item, popped_item)

        # The queue should now have 1 item and that was the item marked
        # as removed.
        self.assertEqual(1, len(self.pq))
        self.assertEqual(0, len(self.pq.entry_finder))

    def test_update_priority_lower(self):
        """When updating the priority of the initial item on the priority queue
        to a lower priority, the updated item should be added to the queue,
        the initial item should be marked as removed, and the initial removed
        from the entry_finder.
        """
        # Set queue to allow updates
        self.pq.allow_priority_updates = True

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        # Update priority of the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 2
        self.pq.push(p_item=updated_item)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(2, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        first_entry = self.pq.peek(0)
        last_entry = self.pq.peek(-1)

        # Last item should be the updated item
        self.assertEqual(2, last_entry.priority)
        self.assertEqual(updated_item, last_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, last_entry.state)

        # First item should be the initial item, with EntryState.REMOVED
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(initial_item, first_entry.p_item)
        self.assertEqual(queues.EntryState.REMOVED, first_entry.state)

        # Item in entry_finder should be the updated item
        item = self.pq.entry_finder[self.pq.get_item_identifier(updated_item.item)]
        self.assertEqual(updated_item.priority, item.priority)
        self.assertEqual(updated_item, item.p_item)
        self.assertEqual(queues.EntryState.ADDED, item.state)

        # When popping off the queue you should end up with the updated_item
        # that now has the lowest priority.
        popped_item = self.pq.pop()
        self.assertEqual(updated_item, popped_item)

        # The queue should now have 0 items, because the removed item was
        # discarded while popping
        self.assertEqual(0, len(self.pq))
        self.assertEqual(0, len(self.pq.entry_finder))

    def test_remove_item(self):
        """When removing an item from the queue, the item should be marked as
        removed, and the item should be removed from the entry_finder.
        """
        # Add an item to the queue
        item = create_p_item(priority=1)
        self.pq.push(p_item=item)

        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        # Remove the item
        self.pq.remove(item)

        first_entry = self.pq.peek(0)

        # First item should be the item with EntryState.REMOVED
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(item, first_entry.p_item)
        self.assertEqual(queues.EntryState.REMOVED, first_entry.state)

        # The queue should now have 1 item and that was the item marked
        # as removed.
        self.assertEqual(1, len(self.pq))
        self.assertEqual(0, len(self.pq.entry_finder))

    def test_push_maxsize_not_allowed(self):
        """When pushing an item to the queue, if the maxsize is reached, the
        item should be discarded.
        """
        # Set maxsize to 1
        self.pq.maxsize = 1

        # Add an item to the queue
        first_item = create_p_item(priority=1)
        self.pq.push(p_item=first_item)

        # Add another item to the queue
        second_item = create_p_item(priority=2)
        with self.assertRaises(_queue.Full):
            self.pq.push(p_item=second_item)

        # The queue should now have 1 item
        self.assertEqual(1, len(self.pq))
        self.assertEqual(1, len(self.pq.entry_finder))

        # The item with the highest priority should be the one that was
        # added first
        first_entry = self.pq.peek(0)
        self.assertEqual(1, first_entry.priority, 1)
        self.assertEqual(first_item, first_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, first_entry.state)

    def test_push_maxsize_allowed(self):
        """When pushing an item to the queue, if the maxsize is reached, the
        item should be discarded.
        """
        # Set maxsize to 0 (unbounded)
        self.pq.maxsize = 0

        # Add an item to the queue
        first_item = create_p_item(priority=1)
        self.pq.push(p_item=first_item)

        # Add another item to the queue
        second_item = create_p_item(priority=2)
        self.pq.push(p_item=second_item)

        # The queue should now have 2 items
        self.assertEqual(2, len(self.pq))
        self.assertEqual(2, len(self.pq.entry_finder))

        first_entry = self.pq.peek(0)
        last_entry = self.pq.peek(-1)

        # The item with the highest priority should be the one that was
        # added first
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(first_item, first_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, first_entry.state)

        # Last item should be the second item
        self.assertEqual(2, last_entry.priority)
        self.assertEqual(second_item, last_entry.p_item)
        self.assertEqual(queues.EntryState.ADDED, last_entry.state)

    def test_pop(self):
        pass

    def test_pop_queue_empty(self):
        pass
