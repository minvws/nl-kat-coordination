import copy
import queue as _queue
import threading
import time
import unittest
import uuid
from typing import Optional
from unittest import mock

from scheduler import config, models, queues, storage

from tests.mocks import queue as mock_queue
from tests.utils import functions


class PriorityQueueTestCase(unittest.TestCase):
    def setUp(self) -> None:
        cfg = config.settings.Settings()
        self.dbconn = storage.DBConn(str(cfg.db_uri))
        models.Base.metadata.create_all(self.dbconn.engine)

        self.pq_store = storage.PriorityQueueStore(self.dbconn)

        self.pq = mock_queue.MockPriorityQueue(
            pq_id="test",
            maxsize=10,
            item_type=functions.TestModel,
            pq_store=self.pq_store,
        )

        self._check_queue_empty()

    def tearDown(self) -> None:
        models.Base.metadata.drop_all(self.dbconn.engine)

    def _check_queue_empty(self):
        self.assertEqual(0, self.pq.qsize())

    def test_push(self):
        """When adding an item to the priority queue, the item should be
        added"""
        item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=item)

        item_db = self.pq_store.get(self.pq.pq_id, item.id)
        self.assertIsNotNone(item_db)
        self.assertEqual(item.id, item_db.id)

        self.assertEqual(1, self.pq.qsize())

    @mock.patch("scheduler.storage.PriorityQueueStore.push")
    def test_push_item_not_found_in_db(self, mock_push):
        """When adding an item to the priority queue, but the item is not
        found in the database, the item shouldn't be added.
        """
        item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)

        mock_push.return_value = None

        with self.assertRaises(queues.errors.PrioritizedItemNotFoundError):
            self.pq.push(p_item=item)

        self.assertEqual(0, self.pq.qsize())
        item_db = self.pq_store.get(self.pq.pq_id, item.id)
        self.assertIsNone(item_db)

    def test_push_incorrect_p_item_type(self):
        """When pushing an item that is not of the correct type, the item
        shouldn't be pushed.
        """
        p_item = {"priority": 1, "data": functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex)}

        with self.assertRaises(queues.errors.InvalidPrioritizedItemError):
            self.pq.push(p_item=p_item)

        self.assertEqual(0, self.pq.qsize())

    def test_push_invalid_p_item(self):
        """When pushing an item that can not be validated, the item shouldn't
        be pushed.
        """
        p_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        p_item.data = {"invalid": "data"}

        with self.assertRaises(queues.errors.InvalidPrioritizedItemError):
            self.pq.push(p_item=p_item)

        self.assertEqual(0, self.pq.qsize())

    def test_push_replace_not_allowed(self):
        """When pushing an item that is already in the queue the item
        shouldn't be pushed.
        """
        # Set queue to not allow duplicates
        self.pq.allow_replace = False

        # Add an item to the queue
        initial_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, self.pq.qsize())

        # Add the same item again
        with self.assertRaises(queues.errors.NotAllowedError):
            self.pq.push(p_item=initial_item)

        self.assertEqual(1, self.pq.qsize())

    def test_push_replace_allowed(self):
        """When pushing an item that is already in the queue, but the queue
        allows duplicates, the item should be pushed.
        """
        # Set queue to allow duplicates
        self.pq.allow_replace = True

        # Add an item to the queue
        initial_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=initial_item)
        self.assertEqual(1, self.pq.qsize())

        # Add the same item again
        self.pq.push(p_item=initial_item)
        self.assertEqual(1, self.pq.qsize())

        # Check if the item on the queue is the replaced item
        updated_item = self.pq_store.get(self.pq.pq_id, initial_item.id)
        self.assertEqual(initial_item.id, updated_item.id)

    def test_push_updates_not_allowed(self):
        """When pushing an item that is already in the queue, and the item is
        updated, the item shouldn't be pushed.
        """
        # Set queue to not allow updates
        self.pq.allow_updates = False

        # Add an item to the queue
        initial_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=initial_item)
        self.assertEqual(1, self.pq.qsize())

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.data["name"] = "updated-name"

        # Add the same item again
        with self.assertRaises(queues.errors.NotAllowedError):
            self.pq.push(p_item=updated_item)

        self.assertEqual(1, self.pq.qsize())

        item_db = self.pq_store.get(self.pq.pq_id, initial_item.id)
        self.assertNotEqual(updated_item.data["name"], item_db.data["name"])

    def test_push_updates_allowed(self):
        """When pushing an item that is already in the queue, and the item is
        updated, but the queue allows item updates, the item should be pushed.
        """
        # Set queue to allow updates
        self.pq.allow_updates = True

        # Add an item to the queue
        initial_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, self.pq.qsize())

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.data["name"] = "updated-name"

        # Add the same item again
        self.pq.push(p_item=updated_item)

        self.assertEqual(1, self.pq.qsize())

        item_db = self.pq_store.get(self.pq.pq_id, initial_item.id)
        self.assertEqual(updated_item.data["name"], item_db.data["name"])

    def test_push_priority_updates_not_allowed(self):
        """When pushing an item that is already in the queue, and the item
        priority is updated, the item shouldn't be pushed.
        """
        # Set queue to disallow priority updates
        self.pq.allow_priority_updates = False

        # Add an item to the queue
        initial_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, self.pq.qsize())

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 100

        # Add the same item again
        with self.assertRaises(queues.errors.NotAllowedError):
            self.pq.push(p_item=updated_item)

        self.assertEqual(1, self.pq.qsize())

        item_db = self.pq_store.get(self.pq.pq_id, initial_item.id)
        self.assertNotEqual(updated_item.priority, item_db.priority)

    def test_push_priority_updates_allowed(self):
        """When pushing an item that is already in the queue, and the item
        priority is updated, the item should be pushed.
        """
        # Set queue to allow priority updates
        self.pq.allow_priority_updates = True

        # Add an item to the queue
        initial_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(1, self.pq.qsize())

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 100

        # Add the same item again
        self.pq.push(p_item=updated_item)

        self.assertEqual(1, self.pq.qsize())

        item_db = self.pq_store.get(self.pq.pq_id, initial_item.id)
        self.assertEqual(updated_item.priority, item_db.priority)

    def test_remove_item(self):
        """When removing an item from the queue, the item should be marked as
        removed, and the item should be removed from the entry_finder.
        """
        # Add an item to the queue
        item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=item)

        self.assertEqual(1, self.pq.qsize())

        # Remove the item
        self.pq_store.remove(self.pq.pq_id, item.id)

        self.assertEqual(0, self.pq.qsize())

    def test_push_maxsize_not_allowed(self):
        """When pushing an item to the queue, if the maxsize is reached, the
        item should be discarded.
        """
        # Set maxsize to 1
        self.pq.maxsize = 1

        # Add an item to the queue
        first_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=first_item)

        # Add another item to the queue
        second_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=2)
        with self.assertRaises(_queue.Full):
            self.pq.push(p_item=second_item)

        # The queue should now have 1 item
        self.assertEqual(1, self.pq.qsize())

        # The item with the highest priority should be the one that was
        # added first
        first_entry = self.pq.peek(0)
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(first_item.data, first_entry.data)

    def test_push_maxsize_allowed(self):
        """When pushing an item to the queue, if the maxsize is not reached, the
        item should be not discarded.
        """
        # Set maxsize to 0 (unbounded)
        self.pq.maxsize = 0

        # Add an item to the queue
        first_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=first_item)

        # Add another item to the queue
        second_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=2)
        self.pq.push(p_item=second_item)

        # The queue should now have 2 items
        self.assertEqual(2, self.pq.qsize())

        first_entry = self.pq.peek(0)
        second_entry = self.pq.peek(1)

        # The item with the highest priority should be the one that was
        # added first
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(first_item.data, first_entry.data)

        # Last item should be the second item
        self.assertEqual(2, second_entry.priority)
        self.assertEqual(second_item.data, second_entry.data)

    def test_push_maxsize_allowed_high_priority(self):
        """When pushing an item to the queue, if the maxsize is reached,
        pushing an item with a higher priority should not discard the item.
        """
        # Set maxsize to 1
        self.pq.maxsize = 1

        # Add an item to the queue
        first_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=first_item)

        # Add another item to the queue
        second_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=second_item)

        # The queue should now have 2 items
        self.assertEqual(2, self.pq.qsize())

        first_entry = self.pq.peek(0)
        second_entry = self.pq.peek(1)

        # The item with the highest priority should be the one that was
        # added first
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(first_item.data, first_entry.data)

        # Last item should be the second item
        self.assertEqual(1, second_entry.priority)
        self.assertEqual(second_item.data, second_entry.data)

    def test_push_maxsize_not_allowed_low_priority(self):
        """When pushing an item to the queue, if the maxsize is reached,
        pushing an item with a lower priority should discard the item.
        """
        # Set maxsize to 1
        self.pq.maxsize = 1

        # Add an item to the queue
        first_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=first_item)

        # Add another item to the queue
        second_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=2)
        with self.assertRaises(_queue.Full):
            self.pq.push(p_item=second_item)

        # The queue should now have 1 item
        self.assertEqual(1, self.pq.qsize())

        # The item with the highest priority should be the one that was
        # added first
        first_entry = self.pq.peek(0)
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(first_item.data, first_entry.data)

    def test_pop(self):
        """When popping an item it should return the correct item and remove
        it from the queue.
        """
        # Add an item to the queue
        first_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=first_item)

        # The queue should now have 1 item
        self.assertEqual(1, self.pq.qsize())

        # Pop the item
        popped_item = self.pq.pop()
        self.assertEqual(first_item.data, popped_item.data)

        # The queue should now be empty
        self.assertEqual(0, self.pq.qsize())

    def test_pop_with_lock(self):
        """When popping an item it should acquire a lock an not allow another
        thread to pop an item.
        """
        # Arrange
        first_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        second_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=first_item)
        self.pq.push(p_item=second_item)

        event = threading.Event()
        queue = _queue.Queue()

        # This function is similar to the pop() function of the queue, but
        # it will set a timeout so we can test the lock.
        def first_pop(event):
            with self.pq.lock:
                item = self.pq_store.pop(self.pq.pq_id, None)

                event.set()
                time.sleep(5)

                self.pq.remove(item)

                queue.put(item)

        def second_pop(event) -> Optional[models.PrioritizedItem]:
            # Wait for thread 1 to set the event before continuing
            event.wait()

            item = self.pq.pop()
            queue.put(item)

        # Act; with thread 1 we will create a lock on the queue, and then with
        # thread 2 we try to pop an item while the lock is active.
        thread1 = threading.Thread(target=first_pop, args=(event,))
        thread2 = threading.Thread(target=second_pop, args=(event,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Assert, we should expect the first item to be popped first
        self.assertEqual(first_item.id, queue.get().id)
        self.assertEqual(second_item.id, queue.get().id)

    def test_pop_without_lock(self):
        """When popping an item it should acquire a lock an not allow another
        thread to pop an item.

        NOTE: Here we test the procedure when a lock isn't set.
        """
        # Arrange
        first_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        second_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=first_item)
        self.pq.push(p_item=second_item)

        event = threading.Event()
        queue = _queue.Queue()

        # This function is similar to the pop() function of the queue, but
        # it will set a timeout. We have omitted the lock here.
        def first_pop(event):
            item = self.pq_store.pop(self.pq.pq_id, None)

            event.set()
            time.sleep(5)

            self.pq.remove(item)

            queue.put(item)

        def second_pop(event) -> Optional[models.PrioritizedItem]:
            # Wait for thread 1 to set the event before continuing
            event.wait()

            item = self.pq.pop()
            queue.put(item)

        # Act; with thread 1 we won't create a lock, and then with thread 2 we
        # try to pop an item while the timeout is active.
        thread1 = threading.Thread(target=first_pop, args=(event,))
        thread2 = threading.Thread(target=second_pop, args=(event,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Assert, we should expect the first item on the second pop
        self.assertEqual(first_item.id, queue.get().id)
        self.assertNotEqual(second_item.id, queue.get().id)

    def test_pop_queue_empty(self):
        """When popping an item from an empty queue, it should raise an
        exception.
        """
        with self.assertRaises(queues.errors.QueueEmptyError):
            self.pq.pop()

    def test_pop_highest_priority(self):
        """Add two items to the queue, and pop the item with the highest
        priority
        """
        # Add an item to the queue
        first_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=first_item)

        # Add another item to the queue
        second_item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=2)
        self.pq.push(p_item=second_item)

        # The queue should now have 2 items
        self.assertEqual(2, self.pq.qsize())

        # Pop the item
        popped_item = self.pq.pop()
        self.assertEqual(first_item.priority, popped_item.priority)

    def test_is_item_on_queue(self):
        """When checking if an item is on the queue, it should return True if
        the item is on the queue, and False if it isn't.
        """
        # Add an item to the queue
        item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)
        self.pq.push(p_item=item)

        # Check if the item is on the queue
        self.assertTrue(self.pq.is_item_on_queue(item))

    def test_is_item_not_on_queue(self):
        """When checking if an item is on the queue, it should return True if
        the item is on the queue, and False if it isn't.
        """
        # Add an item to the queue
        item = functions.create_p_item(scheduler_id=self.pq.pq_id, priority=1)

        # Check if the item is on the queue
        self.assertFalse(self.pq.is_item_on_queue(item))
