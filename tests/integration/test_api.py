import copy
import unittest
import uuid
from unittest import mock

import requests
from fastapi.testclient import TestClient
from scheduler import config, connectors, datastores, models, queues, rankers, schedulers, server
from tests.factories import BoefjeFactory, OOIFactory, OrganisationFactory, ScanProfileFactory


def create_p_item(organisation_id: str, priority: int) -> models.QueuePrioritizedItem:
    scan_profile = ScanProfileFactory(level=0)
    ooi = OOIFactory(scan_profile=scan_profile)
    item = models.QueuePrioritizedItem(
        priority=priority,
        item=models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=organisation_id,
        ),
    )
    return item


class APITestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Datastore
        self.mock_ctx.datastore = datastores.SQLAlchemy(dsn="sqlite:///")
        models.Base.metadata.create_all(self.mock_ctx.datastore.engine)

        # Scheduler
        self.organisation = OrganisationFactory()

        queue = queues.BoefjePriorityQueue(
            pq_id=self.organisation.id,
            maxsize=cfg.pq_maxsize,
            item_type=models.BoefjeTask,
            allow_priority_updates=True,
        )

        ranker = rankers.BoefjeRanker(
            ctx=self.mock_ctx,
        )

        self.scheduler = schedulers.BoefjeScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            queue=queue,
            ranker=ranker,
            organisation=self.organisation,
        )

        self.server = server.Server(self.mock_ctx, {self.scheduler.scheduler_id: self.scheduler})

        self.client = TestClient(self.server.api)

    def test_get_schedulers(self):
        response = self.client.get("/schedulers")
        self.assertEqual(response.status_code, 200)

    def test_get_scheduler(self):
        response = self.client.get(f"/schedulers/{self.scheduler.scheduler_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("id"), self.scheduler.scheduler_id)

    def test_patch_scheduler(self):
        self.assertEqual(True, self.scheduler.populate_queue_enabled)
        response = self.client.patch(
            f"/schedulers/{self.scheduler.scheduler_id}", json={"populate_queue_enabled": False}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(False, response.json().get("populate_queue_enabled"))

    def test_patch_scheduler_attr_not_found(self):
        response = self.client.patch(f"/schedulers/{self.scheduler.scheduler_id}", json={"not_found": "not found"})
        self.assertEqual(response.status_code, 400)

    def test_get_queues(self):
        response = self.client.get("/queues")
        self.assertEqual(response.status_code, 200)

    def test_get_queue(self):
        response = self.client.get(f"/queues/{self.scheduler.scheduler_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("id"), self.scheduler.scheduler_id)

    def test_push_queue(self):
        self.assertEqual(0, self.scheduler.queue.qsize())

        item = create_p_item(self.organisation.id, 0)

        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=item.dict())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_incorrect_item_type(self):
        response = self.client.post(
            f"/queues/{self.scheduler.scheduler_id}/push", json={"priority": 0, "item": "not a task"}
        )
        self.assertEqual(response.status_code, 400)

    def test_push_queue_full(self):
        # Set maxsize of the queue to 1
        self.scheduler.queue.maxsize = 1

        # Add one task to the queue
        first_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=first_item.dict())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Try to add another task to the queue through the api
        second_item = create_p_item(self.organisation.id, 1)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=second_item.dict())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_replace_not_allowed(self):
        """When pushing an item that is already in the queue the item
        shouldn't be pushed.
        """
        # Set queue to not allow duplicates
        self.scheduler.queue.allow_replace = False

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Add the same item again through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())

        # The queue should still have one item
        self.assertEqual(response.status_code, 400)
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_replace_allowed(self):
        # Set queue to not allow duplicates
        self.scheduler.queue.allow_replace = True

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())
        initial_item_id = response.json().get("item").get("id")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Add the same item again through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())

        # The queue should have two items, entry_finder one
        self.assertEqual(response.status_code, 201)
        self.assertEqual(2, self.scheduler.queue.qsize())
        self.assertEqual(1, len(self.scheduler.queue.entry_finder))

        # Check if the item on the queue is the replaced item
        self.assertEqual(initial_item_id, self.scheduler.queue.peek(0).p_item.item.id)

    def test_push_updates_not_allowed(self):
        # Set queue to no allow updates
        self.scheduler.queue.allow_updates = False

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.item.boefje.name = "updated-name"

        # Try to update the item through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=updated_item.dict())

        # The queue should still have one item
        self.assertEqual(response.status_code, 400)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(1, len(self.scheduler.queue.entry_finder))

    def test_push_updates_allowed(self):
        # Set queue to allow updates
        self.scheduler.queue.allow_updates = True

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.item.boefje.name = "updated-name"

        # Try to update the item through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=updated_item.dict())
        self.assertEqual(response.status_code, 201)

        # The queue should have two items, entry_finder one
        self.assertEqual(response.status_code, 201)
        self.assertEqual(2, self.scheduler.queue.qsize())
        self.assertEqual(1, len(self.scheduler.queue.entry_finder))

    def test_push_priority_updates_not_allowed(self):
        # Set queue to no allow updates
        self.scheduler.queue.allow_priority_updates = False

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 1

        # Try to update the item through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=updated_item.dict())

        # The queue should still have one item
        self.assertEqual(response.status_code, 400)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(1, len(self.scheduler.queue.entry_finder))

    def test_push_priority_updates_allowed(self):
        # Set queue to allow updates
        self.scheduler.queue.allow_priority_updates = True

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 1

        # Try to update the item through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=updated_item.dict())

        # The queue should have two items, entry_finder one
        self.assertEqual(response.status_code, 201)
        self.assertEqual(2, self.scheduler.queue.qsize())
        self.assertEqual(1, len(self.scheduler.queue.entry_finder))

    def test_update_priority_higher(self):
        """When updating the priority of the initial item on the priority queue
        to a higher priority, the updated item should be added to the queue,
        the initial item should be marked as removed, and the initial removed
        from the entry_finder.
        """
        # Set queue to allow updates
        self.scheduler.queue.allow_priority_updates = True

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 2)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())
        initial_item_created = models.QueuePrioritizedItem(**response.json())
        self.assertEqual(response.status_code, 201)

        # Update priority of the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 1
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=updated_item.dict())
        updated_item_created = models.QueuePrioritizedItem(**response.json())
        self.assertEqual(response.status_code, 201)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(2, self.scheduler.queue.qsize())
        self.assertEqual(1, len(self.scheduler.queue.entry_finder))

        first_entry = self.scheduler.queue.peek(0)
        last_entry = self.scheduler.queue.peek(-1)

        # Last item should be an item with, EntryState.REMOVED
        self.assertEqual(2, last_entry.priority)
        self.assertEqual(initial_item_created, models.QueuePrioritizedItem(**last_entry.p_item.dict()))
        self.assertEqual(queues.EntryState.REMOVED, last_entry.state)

        # First item should be the updated item, EntryState. ADDED
        self.assertEqual(1, first_entry.priority)
        self.assertEqual(updated_item_created, models.QueuePrioritizedItem(**first_entry.p_item.dict()))
        self.assertEqual(queues.EntryState.ADDED, first_entry.state)

        # Item in entry_finder should be the updated item
        item = self.scheduler.queue.entry_finder[self.scheduler.queue.get_item_identifier(updated_item.item)]
        self.assertEqual(updated_item_created.priority, item.priority)
        self.assertEqual(updated_item_created, models.QueuePrioritizedItem(**item.p_item.dict()))
        self.assertEqual(queues.EntryState.ADDED, item.state)

        # When popping off the queue you should end up with the updated_item
        # that now has the highest priority
        popped_item = self.client.get(f"/queues/{self.scheduler.scheduler_id}/pop")
        self.assertEqual(updated_item_created, models.QueuePrioritizedItem(**popped_item.json()))

        # The queue should now have 1 item and that was the item marked
        # as removed.
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(0, len(self.scheduler.queue.entry_finder))

    def test_update_priority_lower(self):
        """When updating the priority of the initial item on the priority queue
        to a lower priority, the updated item should be added to the queue,
        the initial item should be marked as removed, and the initial removed
        from the entry_finder.
        """
        # Set queue to allow updates
        self.scheduler.queue.allow_priority_updates = True

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 1)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())
        initial_item_created = models.QueuePrioritizedItem(**response.json())
        self.assertEqual(response.status_code, 201)

        # Update priority of the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 2
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=updated_item.dict())
        updated_item_created = models.QueuePrioritizedItem(**response.json())
        self.assertEqual(response.status_code, 201)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(2, self.scheduler.queue.qsize())
        self.assertEqual(1, len(self.scheduler.queue.entry_finder))

        first_entry = self.scheduler.queue.peek(0)
        last_entry = self.scheduler.queue.peek(-1)

        # Last item should be the updated item
        self.assertEqual(2, last_entry.priority)
        self.assertEqual(updated_item_created, models.QueuePrioritizedItem(**last_entry.p_item.dict()))
        self.assertEqual(queues.EntryState.ADDED, last_entry.state)

        # Item in entry_finder should be the updated_item
        item = self.scheduler.queue.entry_finder[self.scheduler.queue.get_item_identifier(updated_item.item)]
        self.assertEqual(updated_item_created.priority, item.priority)
        self.assertEqual(updated_item_created, models.QueuePrioritizedItem(**item.p_item.dict()))
        self.assertEqual(queues.EntryState.ADDED, item.state)

        # When popping off the queue you should end up with the updated item
        # that now has the lowest priority.
        popped_item = self.client.get(f"/queues/{self.scheduler.scheduler_id}/pop")
        self.assertEqual(updated_item_created, models.QueuePrioritizedItem(**popped_item.json()))

        # The queue should now have 1 item, because the removed item was
        # discarded while popping.
        self.assertEqual(0, self.scheduler.queue.qsize())
        self.assertEqual(0, len(self.scheduler.queue.entry_finder))

    def test_pop_queue(self):
        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())
        initial_item_id = response.json().get("item").get("id")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        response = self.client.get(f"/queues/{self.scheduler.scheduler_id}/pop")
        self.assertEqual(200, response.status_code)
        self.assertEqual(initial_item_id, response.json().get("item").get("id"))
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_get_tasks(self):
        response = self.client.get("/tasks")
        self.assertEqual(response.status_code, 200)

    def test_get_task(self):
        # First add a task
        item = create_p_item(self.organisation.id, 0)

        response_post = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=item.dict())
        self.assertEqual(201, response_post.status_code)
        self.assertEqual(1, self.scheduler.queue.qsize())
        initial_item_id = response_post.json().get("item").get("id")

        # Then get the task
        response_get = self.client.get(f"/tasks/{initial_item_id}")
        self.assertEqual(200, response_get.status_code, 200)
        self.assertEqual(initial_item_id, response_get.json().get("task").get("item").get("id"))
