import unittest
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage

from tests.utils import functions


class JobStore(unittest.TestCase):
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
                storage.JobStore.name: storage.JobStore(self.dbconn),
            }
        )

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_create_job(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        job = models.Job(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )

        # Act
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        # Assert
        self.assertEqual(job, self.mock_ctx.datastores.job_store.get_job_by_id(job_db.id))

    def test_get_jobs(self):
        # Arrange
        scheduler_one = "test_scheduler_one"
        for i in range(5):
            job = models.Job(
                scheduler_id=scheduler_one,
                p_item=functions.create_p_item(scheduler_id=scheduler_one, priority=i),
            )
            self.mock_ctx.datastores.job_store.create_job(job)

        scheduler_two = "test_scheduler_two"
        for i in range(5):
            job = models.Job(
                scheduler_id=scheduler_two,
                p_item=functions.create_p_item(scheduler_id=scheduler_two, priority=i),
            )
            self.mock_ctx.datastores.job_store.create_job(job)

        # Act
        jobs_scheduler_one, jobs_scheduler_one_count = self.mock_ctx.datastores.job_store.get_jobs(
            scheduler_id=scheduler_one,
        )
        jobs_scheduler_two, jobs_scheduler_two_count = self.mock_ctx.datastores.job_store.get_jobs(
            scheduler_id=scheduler_two,
        )

        # Assert
        self.assertEqual(5, len(jobs_scheduler_one))
        self.assertEqual(5, jobs_scheduler_one_count)
        self.assertEqual(5, len(jobs_scheduler_two))
        self.assertEqual(5, jobs_scheduler_two_count)

    def test_get_job_by_id(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        job = models.Job(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        # Act
        job_by_id = self.mock_ctx.datastores.job_store.get_job_by_id(job_db.id)

        # Assert
        self.assertEqual(job_by_id.id, job_db.id)

    def test_get_job_by_hash(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        job = models.Job(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        # Act
        job_by_hash = self.mock_ctx.datastores.job_store.get_job_by_hash(job_db.p_item.hash)

        # Assert
        self.assertEqual(job_by_hash.id, job_db.id)
        self.assertEqual(job_by_hash.p_item, job_db.p_item)
        self.assertEqual(job_by_hash.p_item.hash, job_db.p_item.hash)

    def test_update_job(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        job = models.Job(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        # Assert
        self.assertEqual(job_db.enabled, True)

        # Act
        job_db.enabled = False
        self.mock_ctx.datastores.job_store.update_job(job_db)

        # Assert
        job_db_updated = self.mock_ctx.datastores.job_store.get_job_by_id(job_db.id)
        self.assertEqual(job_db_updated.enabled, False)

    def test_update_job_enabled(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        job = models.Job(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        # Assert
        self.assertEqual(job_db.enabled, True)

        # Act
        self.mock_ctx.datastores.job_store.update_job_enabled(job_db.id, False)

        # Assert
        job_db_updated = self.mock_ctx.datastores.job_store.get_job_by_id(job_db.id)
        self.assertEqual(job_db_updated.enabled, False)

    def test_delete_job(self):
        # Arrange
        p_item = functions.create_p_item("test_scheduler_id", 1)

        job = models.Job(
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
        )
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        # Act
        self.mock_ctx.datastores.job_store.delete_job(job_db.id)

        # Assert
        is_job_deleted = self.mock_ctx.datastores.job_store.get_job_by_id(job_db.id)
        self.assertEqual(is_job_deleted, None)

    def test_delete_job_cascade(self):
        """When a job is deleted, its tasks should NOT be deleted."""
        # Arrange
        p_item = functions.create_p_item("test_scheduler_id", 1)

        job = models.Job(
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
        )
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        task = models.Task(
            id=p_item.id,
            hash=p_item.hash,
            type=functions.TestModel.type,
            status=models.TaskStatus.QUEUED,
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
            job_id=job_db.id,
        )
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        self.mock_ctx.datastores.job_store.delete_job(job_db.id)

        # Assert
        is_job_deleted = self.mock_ctx.datastores.job_store.get_job_by_id(job_db.id)
        self.assertEqual(is_job_deleted, None)

        is_task_deleted = self.mock_ctx.datastores.task_store.get_task_by_id(task_db.id)
        self.assertIsNotNone(is_task_deleted)
        self.assertIsNone(is_task_deleted.job_id)

    def test_relationship_job_tasks(self):
        # Arrange
        p_item = functions.create_p_item("test_scheduler_id", 1)

        job = models.Job(
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
        )
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        task = models.Task(
            id=p_item.id,
            hash=p_item.hash,
            type=functions.TestModel.type,
            status=models.TaskStatus.QUEUED,
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
            job_id=job_db.id,
        )
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        job_tasks = self.mock_ctx.datastores.job_store.get_job_by_id(job_db.id).tasks

        # Assert
        self.assertEqual(len(job_tasks), 1)
        self.assertEqual(job_tasks[0].id, task_db.id)
