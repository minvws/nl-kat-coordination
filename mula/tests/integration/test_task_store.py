import json
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage
from scheduler.storage import filters

from tests.factories import OrganisationFactory
from tests.utils import functions


class TaskStoreTestCase(unittest.TestCase):
    def setUp(self):
        # Application Context
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = config.settings.Settings()

        # Database
        self.dbconn = storage.DBConn(str(self.mock_ctx.config.db_uri))
        models.Base.metadata.drop_all(self.dbconn.engine)
        models.Base.metadata.create_all(self.dbconn.engine)

        self.mock_ctx.datastores = SimpleNamespace(
            **{
                storage.TaskStore.name: storage.TaskStore(self.dbconn),
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(self.dbconn),
            }
        )

        # Organisation
        self.organisation = OrganisationFactory()

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_get_status_counts(self):
        # Arrange
        one_hour = datetime.now(timezone.utc) - timedelta(hours=1)
        four_hours = datetime.now(timezone.utc) - timedelta(hours=4)
        twenty_three_hours = datetime.now(timezone.utc) - timedelta(hours=23)
        twenty_five_hours = datetime.now(timezone.utc) - timedelta(hours=25)

        for r, status, modified_at in zip(
            (
                range(2),
                range(2),
                range(2),
                range(2),
                range(2),
            ),
            (
                models.TaskStatus.QUEUED,
                models.TaskStatus.COMPLETED,
                models.TaskStatus.FAILED,
                models.TaskStatus.DISPATCHED,
                models.TaskStatus.DISPATCHED,
            ),
            (
                one_hour,
                four_hours,
                one_hour,
                twenty_five_hours,
                twenty_three_hours,
            ),
        ):
            for _ in r:
                p_item = functions.create_p_item(self.organisation.id, 1)
                task = models.Task(
                    id=p_item.id,
                    hash=p_item.hash,
                    type=functions.TestModel.type,
                    scheduler_id=p_item.scheduler_id,
                    p_item=p_item,
                    status=status,
                    modified_at=modified_at,
                )
                self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        results = self.mock_ctx.datastores.task_store.get_status_counts()

        # Assert
        self.assertEqual(results[models.TaskStatus.QUEUED], 2)
        self.assertEqual(results[models.TaskStatus.COMPLETED], 2)
        self.assertEqual(results[models.TaskStatus.FAILED], 2)
        self.assertEqual(results[models.TaskStatus.DISPATCHED], 4)

    def test_get_status_count_per_hour(self):
        # Arrange
        one_hour = datetime.now(timezone.utc) - timedelta(hours=1)
        four_hours = datetime.now(timezone.utc) - timedelta(hours=4)
        twenty_three_hours = datetime.now(timezone.utc) - timedelta(hours=23)
        twenty_five_hours = datetime.now(timezone.utc) - timedelta(hours=25)

        for r, status, modified_at in zip(
            (
                range(2),
                range(2),
                range(2),
                range(2),
                range(2),
            ),
            (
                models.TaskStatus.QUEUED,
                models.TaskStatus.COMPLETED,
                models.TaskStatus.FAILED,
                models.TaskStatus.DISPATCHED,
                models.TaskStatus.DISPATCHED,
            ),
            (
                one_hour,
                four_hours,
                one_hour,
                twenty_five_hours,
                twenty_three_hours,
            ),
        ):
            for _ in r:
                p_item = functions.create_p_item(self.organisation.id, 1)
                task = models.Task(
                    id=p_item.id,
                    hash=p_item.hash,
                    type=functions.TestModel.type,
                    scheduler_id=p_item.scheduler_id,
                    p_item=p_item,
                    status=status,
                    modified_at=modified_at,
                )
                self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        results = self.mock_ctx.datastores.task_store.get_status_count_per_hour()
        keys = [k for k in results]

        # Assert
        self.assertEqual(len(results), 3)
        self.assertEqual(results.get(keys[0]).get("dispatched"), 2)
        self.assertEqual(results.get(keys[0]).get("total"), 2)
        self.assertEqual(results.get(keys[1]).get("completed"), 2)
        self.assertEqual(results.get(keys[1]).get("total"), 2)
        self.assertEqual(results.get(keys[2]).get("queued"), 2)

    def test_get_tasks_filter_multiple_and(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        f_req = filters.FilterRequest(
            filters={
                "and": [
                    filters.Filter(
                        column="id",
                        field=None,
                        operator="eq",
                        value=first_task.id.hex,
                    ),
                    filters.Filter(
                        column="p_item",
                        field="data__id",
                        operator="eq",
                        value=first_p_item.data.get("id"),
                    ),
                ]
            },
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, first_task.id)

    def test_get_tasks_filter_multiple_or(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters={
                "or": [
                    filters.Filter(
                        column="id",
                        field=None,
                        operator="eq",
                        value=first_task.id.hex,
                    ),
                    filters.Filter(
                        column="id",
                        field=None,
                        operator="eq",
                        value=second_task.id.hex,
                    ),
                ]
            },
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 2)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, second_task.id)
        self.assertEqual(tasks[1].id, first_task.id)

    def test_get_tasks_filter_multiple_not(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1, categories=["test-a", "test-b"]),
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2, categories=["test-a"]),
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        third_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=3, categories=["test-b"]),
        )
        third_task = functions.create_task(third_p_item)
        self.mock_ctx.datastores.task_store.create_task(third_task)

        f_req = filters.FilterRequest(
            filters={
                "and": [
                    filters.Filter(
                        column="id",
                        field=None,
                        operator="eq",
                        value=first_task.id.hex,
                    ),
                    filters.Filter(
                        column="p_item",
                        field="data",
                        operator="@>",
                        value=json.dumps({"categories": ["test-a"]}),
                    ),
                ],
                "not": [
                    filters.Filter(
                        column="p_item",
                        field="data__count",
                        operator=">",
                        value=1,
                    ),
                ],
            },
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, first_task.id)

    def test_get_tasks_filter_eq(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="id",
                    field=None,
                    operator="eq",
                    value=first_task.id.hex,
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, first_task.id)

    def test_get_tasks_filter_ne(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="id",
                    field=None,
                    operator="ne",
                    value=first_task.id.hex,
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, second_task.id)

    def test_get_tasks_filter_json_eq(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="eq",
                    value=first_p_item.data.get("id"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].p_item.data["id"], first_p_item.data.get("id"))

        # Arrange
        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="==",
                    value=first_p_item.data.get("id"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].p_item.data["id"], first_p_item.data.get("id"))

    def test_get_tasks_filter_json_ne(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="ne",
                    value=second_p_item.data.get("id"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].p_item.data["id"], first_p_item.data.get("id"))

    def test_get_tasks_filter_json_gt(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1)
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2)
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="gt",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, second_task.id)

        # Arrange
        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator=">",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, second_task.id)

    def test_get_tasks_filter_json_gte(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1)
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2)
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="gte",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 2)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, second_task.id)
        self.assertEqual(tasks[1].id, first_task.id)

        # Arrange
        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator=">=",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 2)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, second_task.id)
        self.assertEqual(tasks[1].id, first_task.id)

    def test_get_tasks_filter_json_lt(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2)
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1)
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="lt",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, second_task.id)

        # Arrange
        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="<",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, second_task.id)

    def test_get_tasks_filter_json_lte(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2)
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1)
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="lte",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 2)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, second_task.id)
        self.assertEqual(tasks[1].id, first_task.id)

        # Arrange
        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="<=",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 2)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, second_task.id)
        self.assertEqual(tasks[1].id, first_task.id)

    def test_get_tasks_filter_json_like(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="like",
                    value=f"%{first_p_item.data.get('name')[0:10]}%",
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, first_task.id)

    def test_get_tasks_filter_json_not_like(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="not_like",
                    value=f"%{first_p_item.data.get('name')[0:10]}%",
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, second_task.id)

    def test_get_tasks_filter_json_ilike(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="ilike",
                    value=f"%{first_p_item.data.get('name')[0:10].upper()}%",
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, first_task.id)

    def test_get_tasks_filter_json_not_ilike(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="not_ilike",
                    value=f"%{first_p_item.data.get('name')[0:10].upper()}%",
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, second_task.id)

    def test_get_tasks_filter_json_in(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="in",
                    value=[first_p_item.data.get("name"), second_p_item.data.get("name")],
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 2)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, second_task.id)
        self.assertEqual(tasks[1].id, first_task.id)

    def test_get_tasks_filter_json_not_in(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="not_in",
                    value=[first_p_item.data.get("name")],
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, second_task.id)

    def test_get_tasks_filter_json_contains(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="contains",
                    value=first_p_item.data.get("name")[0:10],
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, first_task.id)

    def test_get_tasks_filter_json_starts_with(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="starts_with",
                    value=first_p_item.data.get("name")[0:10],
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, first_task.id)

    def test_get_tasks_filter_jsonb_contains(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1, categories=["test-a", "test-b"]),
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2, categories=["test-a"]),
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        third_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=3, categories=["test-b"]),
        )
        third_task = functions.create_task(third_p_item)
        self.mock_ctx.datastores.task_store.create_task(third_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data",
                    operator="@>",
                    value=json.dumps({"categories": ["test-a"]}),
                )
            ],
        )

        # Act
        tasks, count = self.mock_ctx.datastores.task_store.get_tasks(filters=f_req)

        # Assert
        self.assertEqual(count, 2)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, second_task.id)
        self.assertEqual(tasks[1].id, first_task.id)

    def test_get_tasks_filter_json_mismatch(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="eq",
                    value=False,
                )
            ],
        )

        # Act
        with self.assertRaises(ValueError):
            tasks, count = self.mock_ctx.datastores.task_store.get_tasks(
                filters=f_req,
            )
