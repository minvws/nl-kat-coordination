import copy
import json
import unittest
import uuid
from datetime import datetime, timedelta
from unittest import mock

from fastapi.testclient import TestClient
from scheduler import config, models, queues, rankers, repositories, schedulers, server
from tests.factories import OrganisationFactory
from tests.utils import functions
from tests.utils.functions import create_p_item


class MockPriorityQueue(queues.PriorityQueue):
    def create_hash(self, item: functions.TestModel):
        return hash(item.id)


class APITemplateTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Datastore
        self.mock_ctx.datastore = repositories.sqlalchemy.SQLAlchemy("sqlite:///")
        models.Base.metadata.create_all(self.mock_ctx.datastore.engine)

        self.pq_store = repositories.sqlalchemy.PriorityQueueStore(self.mock_ctx.datastore)
        self.task_store = repositories.sqlalchemy.TaskStore(self.mock_ctx.datastore)

        self.mock_ctx.pq_store = self.pq_store
        self.mock_ctx.task_store = self.task_store

        # Scheduler
        self.organisation = OrganisationFactory()

        queue = MockPriorityQueue(
            pq_id=self.organisation.id,
            maxsize=10,
            item_type=functions.TestModel,
            allow_priority_updates=True,
            pq_store=self.pq_store,
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


class APITestCase(APITemplateTestCase):
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

        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_incorrect_item_type(self):
        response = self.client.post(
            f"/queues/{self.scheduler.scheduler_id}/push", json={"priority": 0, "item": "not a task"}
        )
        self.assertEqual(response.status_code, 422)

    def test_push_queue_full(self):
        # Set maxsize of the queue to 1
        self.scheduler.queue.maxsize = 1

        # Add one task to the queue
        first_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(first_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Try to add another task to the queue through the api
        second_item = create_p_item(self.organisation.id, 1)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(second_item.json()))
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
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(initial_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Add the same item again through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(initial_item.json()))

        # The queue should still have one item
        self.assertEqual(response.status_code, 400)
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_replace_allowed(self):
        # Set queue to not allow duplicates
        self.scheduler.queue.allow_replace = True

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(initial_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Add the same item again through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=response.json())

        # The queue should have one item
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Check if the item on the queue is the replaced item
        self.assertEqual(response.json().get("id"), str(self.scheduler.queue.peek(0).id))

    def test_push_updates_not_allowed(self):
        # Set queue to no allow updates
        self.scheduler.queue.allow_updates = False

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(initial_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Update the item
        updated_item = models.PrioritizedItem(**response.json())
        updated_item.data["name"] = "updated-name"

        # Try to update the item through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(updated_item.json()))

        # The queue should still have one item
        self.assertEqual(response.status_code, 400)
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_updates_allowed(self):
        # Set queue to allow updates
        self.scheduler.queue.allow_updates = True

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(initial_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Update the item
        updated_item = models.PrioritizedItem(**response.json())
        updated_item.data["name"] = "updated-name"

        # Try to update the item through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(updated_item.json()))
        self.assertEqual(response.status_code, 201)

        # The queue should have one item
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Check if the item on the queue is the updated item
        self.assertEqual(response.json().get("id"), str(self.scheduler.queue.peek(0).id))
        self.assertEqual(response.json().get("data").get("name"), "updated-name")

    def test_push_priority_updates_not_allowed(self):
        # Set queue to no allow updates
        self.scheduler.queue.allow_priority_updates = False

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(initial_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 1

        # Try to update the item through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(updated_item.json()))

        # The queue should still have one item
        self.assertEqual(response.status_code, 400)
        self.assertEqual(1, self.scheduler.queue.qsize())

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
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(initial_item.json()))
        self.assertEqual(response.status_code, 201)

        # Update priority of the item
        updated_item = models.PrioritizedItem(**response.json())
        updated_item.priority = 1

        # Try to update the item through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(updated_item.json()))
        self.assertEqual(response.status_code, 201)

        # The queue should have one item
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Check if the item on the queue is the updated item
        self.assertEqual(response.json().get("id"), str(self.scheduler.queue.peek(0).id))

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
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(initial_item.json()))
        self.assertEqual(response.status_code, 201)

        # Update priority of the item
        updated_item = models.PrioritizedItem(**response.json())
        updated_item.priority = 2

        # Try to update the item through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(updated_item.json()))
        self.assertEqual(response.status_code, 201)

        # The queue should have one item
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Check if the item on the queue is the updated item
        self.assertEqual(response.json().get("id"), str(self.scheduler.queue.peek(0).id))

    def test_pop_queue(self):
        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(initial_item.json()))
        initial_item_id = response.json().get("id")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        response = self.client.get(f"/queues/{self.scheduler.scheduler_id}/pop")
        self.assertEqual(200, response.status_code)
        self.assertEqual(initial_item_id, response.json().get("id"))
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_pop_queue_filters(self):
        # Add one task to the queue
        first_item = create_p_item(self.organisation.id, 0, data=functions.TestModel(id="123", name="test"))
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(first_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Add second item to the queue
        second_item = create_p_item(self.organisation.id, 1, data=functions.TestModel(id="456", name="test"))
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(second_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(2, self.scheduler.queue.qsize())

        # Should get the first item
        response = self.client.get(
            f"/queues/{self.scheduler.scheduler_id}/pop", json=[{"field": "name", "operator": "eq", "value": "test"}]
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(str(first_item.id), response.json().get("id"))
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Should not return any items
        response = self.client.get(
            f"/queues/{self.scheduler.scheduler_id}/pop", json=[{"field": "id", "operator": "eq", "value": "123"}]
        )
        self.assertEqual(404, response.status_code)
        self.assertEqual({"detail": "could not pop item from queue, check your filters"}, response.json())
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Should get the second item
        response = self.client.get(
            f"/queues/{self.scheduler.scheduler_id}/pop", json=[{"field": "name", "operator": "eq", "value": "test"}]
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(str(second_item.id), response.json().get("id"))
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_pop_empty(self):
        """When queue is empty it should return an empty response"""
        response = self.client.get(f"/queues/{self.scheduler.scheduler_id}/pop")
        self.assertEqual(200, response.status_code)


class APITasksEndpointTestCase(APITemplateTestCase):
    def setUp(self):
        super().setUp()

        # Add one task to the queue
        first_item = create_p_item(
            self.organisation.id,
            0,
            data=functions.TestModel(
                id="123",
                name="test",
                child=functions.TestModel(id="123.123", name="test.child"),
            ),
        )
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(first_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(1, self.scheduler.queue.qsize())

        self.first_item_api = self.client.get(f"/tasks/{first_item.id}").json()

        # Add second item to the queue
        second_item = create_p_item(
            self.organisation.id,
            1,
            data=functions.TestModel(id="456", name="test"),
        )
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(second_item.json()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(2, self.scheduler.queue.qsize())

        self.second_item_api = self.client.get(f"/tasks/{second_item.id}").json()

    def test_create_task(self):
        item = create_p_item(self.organisation.id, 0)
        response_post = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(item.json()))
        self.assertEqual(201, response_post.status_code)

        initial_item_id = response_post.json().get("id")
        response_get = self.client.get(f"/tasks/{initial_item_id}")
        self.assertEqual(200, response_get.status_code)

    def test_get_tasks(self):
        response = self.client.get("/tasks")
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, response.json()["count"])
        self.assertEqual(2, len(response.json()["results"]))

    def test_get_task(self):
        # First add a task
        item = create_p_item(self.organisation.id, 0)

        response_post = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=json.loads(item.json()))
        self.assertEqual(201, response_post.status_code)
        initial_item_id = response_post.json().get("id")

        # Then get the task
        response_get = self.client.get(f"/tasks/{initial_item_id}")
        self.assertEqual(200, response_get.status_code, 200)
        self.assertEqual(initial_item_id, response_get.json().get("id"))

    def test_get_tasks_value(self):
        # Get tasks with embedded value of "test"", should return 2 items
        response = self.client.get("/tasks", json=[{"field": "data__name", "operator": "eq", "value": "test"}])
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(response.json()["results"]))

        # Get tasks with embedded value of "123", should return 1 item
        response = self.client.get("/tasks", json=[{"field": "data__id", "operator": "eq", "value": "123"}])
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json()["results"]))
        self.assertEqual("123", response.json()["results"][0]["p_item"]["data"]["id"])

        # Get tasks with embedded value of 123 two level deep, should return 1 item
        response = self.client.get(
            "/tasks", json=[{"field": "data__child__name", "operator": "eq", "value": "test.child"}]
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json()["results"]))
        self.assertEqual("123.123", response.json()["results"][0]["p_item"]["data"]["child"]["id"])

    def test_get_tasks_min_and_max_created_at(self):
        # Get tasks based on datetime, both min_created_at and max_created_at, should return 2 items
        min_created_at = self.first_item_api.get("created_at")
        max_created_at = self.second_item_api.get("created_at")
        response = self.client.get(f"/tasks?min_created_at={min_created_at}&max_created_at={max_created_at}")
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(response.json()["results"]))

        # Get tasks based on datetime, both min_created_at and max_created_at, should return 1 item
        min_created_at = self.first_item_api.get("created_at")
        max_created_at = self.first_item_api.get("created_at")
        response = self.client.get(f"/tasks?min_created_at={min_created_at}&max_created_at={max_created_at}")
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json()["results"]))

    def test_get_tasks_min_created_at(self):
        # Get tasks based on datetime, only min_created_at, should return 2 items
        response = self.client.get(f"/tasks?min_created_at={self.first_item_api.get('created_at')}")
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(response.json()["results"]))

        # Get tasks based on datetime, only min_created_at, should return 1 item
        response = self.client.get(f"/tasks?min_created_at={self.second_item_api.get('created_at')}")
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json()["results"]))
        self.assertEqual(self.second_item_api.get("id"), response.json()["results"][0]["id"])

    def test_get_tasks_max_created_at(self):
        # Get tasks based on datetime, only max_created_at, should return 2 items
        response = self.client.get(f"/tasks?max_created_at={self.second_item_api.get('created_at')}")
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(response.json()["results"]))

        # Get tasks based on datetime, only max_created_at, should return 1 item
        response = self.client.get(f"/tasks?max_created_at={self.first_item_api.get('created_at')}")
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json()["results"]))
        self.assertEqual(self.first_item_api.get("id"), response.json()["results"][0]["id"])

    def test_get_tasks_min_greater_than_max_created_at(self):
        # Get tasks min_created_at greater than max_created_at, should return an error
        min_created_at = self.second_item_api.get("created_at")
        max_created_at = self.first_item_api.get("created_at")
        response = self.client.get(f"/tasks?min_created_at={min_created_at}&max_created_at={max_created_at}")
        self.assertEqual(400, response.status_code)

    def test_get_tasks_min_created_at_future(self):
        # Get tasks based on datetime for something in the future, should return 0 items
        response = self.client.get(f"/tasks?min_created_at={datetime.now() + timedelta(seconds=10)}")
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(response.json()["results"]))

    def test_patch_tasks(self):
        # Patch a task
        self.assertEqual("queued", self.first_item_api.get("status"))
        response = self.client.patch(f"/tasks/{self.first_item_api.get('id')}", json={"status": "completed"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("completed", response.json().get("status"))

    def test_patch_task_empty(self):
        # Patch a task with empty body
        response = self.client.patch(f"/tasks/{self.first_item_api.get('id')}", json={})
        self.assertEqual(400, response.status_code)
        self.assertEqual("no data to patch", response.json().get("detail"))

    def test_patch_task_not_found(self):
        # Patch a task that does not exist
        response = self.client.patch(f"/tasks/{uuid.uuid4().hex}", json={"status": "completed"})
        self.assertEqual(404, response.status_code)
        self.assertEqual("task not found", response.json().get("detail"))

    def test_patch_task_malformed_id(self):
        # Patch a task with malformed id
        response = self.client.patch("/tasks/123.123", json={"status": "completed"})
        self.assertEqual(400, response.status_code)
        self.assertIn("failed to get task", response.json().get("detail"))
