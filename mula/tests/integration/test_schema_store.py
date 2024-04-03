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
        schema = models.Schema(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(schemar_id=scheduler_id, priority=1),
        )

        # Act
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Assert
        self.assertEqual(schema, self.mock_ctx.datastores.schema_store.get_schema_by_id(schema_db.id))

    def test_get_schemas(self):
        # Arrange
        scheduler_one = "test_scheduler_one"
        for i in range(5):
            schema = models.Schema(
                scheduler_id=scheduler_one,
                p_item=functions.create_p_item(schemar_id=scheduler_one, priority=i),
            )
            self.mock_ctx.datastores.schema_store.create_schema(schema)

        scheduler_two = "test_scheduler_two"
        for i in range(5):
            schema = models.Schema(
                scheduler_id=scheduler_two,
                p_item=functions.create_p_item(schemar_id=scheduler_two, priority=i),
            )
            self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Act
        schemas_scheduler_one, schedules_scheduler_one_count = self.mock_ctx.datastores.schema_store.get_schedules(
            scheduler_id=scheduler_one,
        )
        schemas_scheduler_two, schedules_scheduler_two_count = self.mock_ctx.datastores.schema_store.get_schedules(
            scheduler_id=scheduler_two,
        )

        # Assert
        self.assertEqual(5, len(schemas_scheduler_one))
        self.assertEqual(5, schemas_scheduler_one_count)
        self.assertEqual(5, len(schemas_scheduler_two))
        self.assertEqual(5, schemas_scheduler_two_count)

    def test_get_schema_by_id(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        schema = models.Schema(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(schemar_id=scheduler_id, priority=1),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Act
        schema_by_id = self.mock_ctx.datastores.schema_store.get_schema_by_id(schema_db.id)

        # Assert
        self.assertEqual(schema_by_id.id, schema_db.id)

    def test_get_schema_by_hash(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        schema = models.Schema(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(schemar_id=scheduler_id, priority=1),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Act
        schema_by_hash = self.mock_ctx.datastores.schema_store.get_schema_by_hash(schema_db.p_item.hash)

        # Assert
        self.assertEqual(schema_by_hash.id, schema_db.id)
        self.assertEqual(schema_by_hash.p_item, schema_db.p_item)
        self.assertEqual(schema_by_hash.p_item.hash, schema_db.p_item.hash)

    def test_update_schema(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        schema = models.Schema(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(schemar_id=scheduler_id, priority=1),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Assert
        self.assertEqual(schema_db.enabled, True)

        # Act
        schema_db.enabled = False
        self.mock_ctx.datastores.schema_store.update_schema(schema_db)

        # Assert
        schema_db_updated = self.mock_ctx.datastores.schema_store.get_schema_by_id(schema_db.id)
        self.assertEqual(schema_db_updated.enabled, False)

    def test_update_schema_enabled(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        schema = models.Schema(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(schemar_id=scheduler_id, priority=1),
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Assert
        self.assertEqual(schema_db.enabled, True)

        # Act
        self.mock_ctx.datastores.schema_store.update_schema_enabled(schema_db.id, False)

        # Assert
        schema_db_updated = self.mock_ctx.datastores.schema_store.get_schema_by_id(schema_db.id)
        self.assertEqual(schema_db_updated.enabled, False)

    def test_delete_schema(self):
        # Arrange
        p_item = functions.create_p_item("test_scheduler_id", 1)

        schema = models.Schema(
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        # Act
        self.mock_ctx.datastores.schema_store.delete_schema(schema_db.id)

        # Assert
        is_schema_deleted = self.mock_ctx.datastores.schema_store.get_schema_by_id(schema_db.id)
        self.assertEqual(is_schema_deleted, None)

    def test_delete_schema_cascade(self):
        """When a schema is deleted, its tasks should NOT be deleted."""
        # Arrange
        p_item = functions.create_p_item("test_scheduler_id", 1)

        schema = models.Schema(
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        task = models.TaskRun(
            id=p_item.id,
            hash=p_item.hash,
            type=functions.TestModel.type,
            status=models.TaskStatus.QUEUED,
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
            schema_id=schema_db.id,
        )
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        self.mock_ctx.datastores.schema_store.delete_schema(schema_db.id)

        # Assert
        is_schema_deleted = self.mock_ctx.datastores.schema_store.get_schema_by_id(schema_db.id)
        self.assertEqual(is_schema_deleted, None)

        is_task_deleted = self.mock_ctx.datastores.task_store.get_task(task_db.id)
        self.assertIsNotNone(is_task_deleted)
        self.assertIsNone(is_task_deleted.schema_id)

    def test_relationship_schema_tasks(self):
        # Arrange
        p_item = functions.create_p_item("test_scheduler_id", 1)

        schema = models.Schema(
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
        )
        schema_db = self.mock_ctx.datastores.schema_store.create_schema(schema)

        task = models.TaskRun(
            id=p_item.id,
            hash=p_item.hash,
            type=functions.TestModel.type,
            status=models.TaskStatus.QUEUED,
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
            schema_id=schema_db.id,
        )
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        schema_tasks = self.mock_ctx.datastores.schema_store.get_schema_by_id(schema_db.id).tasks

        # Assert
        self.assertEqual(len(schema_tasks), 1)
        self.assertEqual(schema_tasks[0].id, task_db.id)
