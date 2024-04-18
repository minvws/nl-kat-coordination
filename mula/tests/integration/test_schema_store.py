import unittest
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage
from tests.utils import functions


class SchemaStore(unittest.TestCase):
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
                storage.SchemaStore.name: storage.SchemaStore(self.dbconn),
            }
        )

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_create_schema(self):
        # Arrange
        scheduler_id = "test_scheduler_id"

        task = functions.create_p_item(scheduler_id, 1)
        schema = models.TaskSchema(
            scheduler_id=scheduler_id,
            hash=task.hash,
            data=task.model_dump(),
        )

        # Act
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Assert
        self.assertEqual(schema, schema_db)

    # TODO: review and fix this
    def test_get_schemas(self):
        # Arrange
        scheduler_one = "test_scheduler_one"
        for i in range(5):
            task = functions.create_p_item(scheduler_one, 1)
            schema = models.TaskSchema(
                scheduler_id=scheduler_one,
                hash=task.hash,
                data=task.model_dump(),
            )
            self.mock_ctx.datastores.schema_store.create_schema(schema)

        scheduler_two = "test_scheduler_two"
        for i in range(5):
            task = functions.create_p_item(scheduler_two, 1)
            schema = models.TaskSchema(
                scheduler_id=scheduler_two,
                hash=task.hash,
                data=task.model_dump(),
            )
            self.mock_ctx.datastores.schema_store.create_schema(schema)

        # FIXME: should this be done on the scheduler_id or something else?
        # Act
        schemas_scheduler_one, schemas_scheduler_one_count = self.mock_ctx.datastores.schema_store.get_schemas(
            scheduler_id=scheduler_one,
        )
        schemas_scheduler_two, schemas_scheduler_two_count = self.mock_ctx.datastores.schema_store.get_schemas(
            scheduler_id=scheduler_two,
        )

        # Assert
        self.assertEqual(5, len(schemas_scheduler_one))
        self.assertEqual(5, schemas_scheduler_one_count)
        self.assertEqual(5, len(schemas_scheduler_two))
        self.assertEqual(5, schemas_scheduler_two_count)

    def test_get_schema(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        task = functions.create_p_item(scheduler_id, 1)
        schema = models.TaskSchema(
            scheduler_id=scheduler_id,
            hash=task.hash,
            data=task.model_dump(),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Act
        schema_by_id = self.mock_ctx.datastores.schema_store.get_schema(schema_db.id)

        # Assert
        self.assertEqual(schema_by_id.id, schema_db.id)

    def test_get_schema_by_hash(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        data = functions.create_test_model()
        schema = models.TaskSchema(
            scheduler_id=scheduler_id,
            hash=data.hash,
            data=data.model_dump(),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Act
        schema_by_hash = self.mock_ctx.datastores.schema_store.get_schema_by_hash(schema_db.hash)

        # Assert
        self.assertEqual(schema_by_hash.id, schema_db.id)
        self.assertEqual(schema_by_hash.data, schema_db.data)
        self.assertEqual(schema_by_hash.hash, schema_db.hash)

    def test_update_schema(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        task = functions.create_p_item(scheduler_id, 1)
        schema = models.TaskSchema(
            scheduler_id=scheduler_id,
            hash=task.hash,
            data=task.model_dump(),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Assert
        self.assertEqual(schema_db.enabled, True)

        # Act
        schema_db.enabled = False
        self.mock_ctx.datastores.schema_store.update_schema(schema_db)

        # Assert
        schema_db_updated = self.mock_ctx.datastores.schema_store.get_schema(schema_db.id)
        self.assertEqual(schema_db_updated.enabled, False)

    def test_delete_schema(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        task = functions.create_p_item(scheduler_id, 1)
        schema = models.TaskSchema(
            scheduler_id=scheduler_id,
            hash=task.hash,
            data=task.model_dump(),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Act
        self.mock_ctx.datastores.schema_store.delete_schema(schema_db.id)

        # Assert
        is_schema_deleted = self.mock_ctx.datastores.schema_store.get_schema(schema_db.id)
        self.assertEqual(is_schema_deleted, None)

    # TODO: review and fix this
    def test_delete_schema_cascade(self):
        """When a schema is deleted, its tasks should NOT be deleted."""
        # Arrange
        scheduler_id = "test_scheduler_id"
        task = functions.create_p_item(scheduler_id, 1)
        schema = models.TaskSchema(
            scheduler_id=scheduler_id,
            hash=task.hash,
            data=task.model_dump(),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        task.schema_id = schema_db.id
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        self.mock_ctx.datastores.schema_store.delete_schema(schema_db.id)

        # Assert
        is_schema_deleted = self.mock_ctx.datastores.schema_store.get_schema(schema_db.id)
        self.assertEqual(is_schema_deleted, None)

        is_task_deleted = self.mock_ctx.datastores.task_store.get_task(task_db.id)
        self.assertIsNotNone(is_task_deleted)
        self.assertIsNone(is_task_deleted.schema_id)

    def test_relationship_schema_tasks(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        task = functions.create_task(scheduler_id)
        schema = models.TaskSchema(
            scheduler_id=scheduler_id,
            hash=task.hash,
            data=task.model_dump(),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        task.schema_id = schema_db.id
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        schema_tasks = self.mock_ctx.datastores.schema_store.get_schema(schema_db.id).tasks

        # Assert
        self.assertEqual(len(schema_tasks), 1)
        self.assertEqual(schema_tasks[0].id, task_db.id)

    @unittest.skip("Transfer this to test_schema_store.py")
    def test_get_tasks_filter_related(self):
        # Arrange
        task = functions.create_task(scheduler_id=self.organisation.id)
        schema = functions.create_schema(self.organisation.id, task)

        task.schema_id = schema.id
        created_task = self.mock_ctx.datastores.task_store.create_task(task)

        f_req = filters.FilterRequest(
            filters={
                "and": [
                    filters.Filter(
                        column="",
                        field="id",
                        operator="eq",
                        value=created_task.id.hex,
                    ),
                ]
            }
        )

        task_runs, count = self.mock_ctx.datastores.task_store.get_runs(filters=f_req)
        self.assertEqual(count, 1)
        self.assertEqual(len(task_runs), 1)
        self.assertEqual(task_runs[0].task_id, created_task.id)

    @unittest.skip("Transfer this to test_schema_store.py")
    def test_get_tasks_filter_related_and_nested(self):
        # Arrange
        task = functions.create_task(scheduler_id=self.organisation.id)
        created_task = self.mock_ctx.datastores.task_store.create_task(task)

        task_run = functions.create_run(task)
        created_run = self.mock_ctx.datastores.task_store.create_run(task_run)

        f_req = filters.FilterRequest(
            filters={
                "and": [
                    filters.Filter(
                        column="task",
                        field="data__id",
                        operator="eq",
                        value=created_task.data.get("id"),
                    ),
                ]
            }
        )

        task_runs, count = self.mock_ctx.datastores.task_store.get_runs(filters=f_req)
        self.assertEqual(count, 1)
        self.assertEqual(len(task_runs), 1)
        self.assertEqual(task_runs[0].task_id, created_task.id)
