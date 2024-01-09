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
            hash="test_hash",
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
                hash=f"test_hash_{i}",
                p_item=functions.create_p_item(scheduler_id=scheduler_one, priority=i),
            )
            self.mock_ctx.datastores.job_store.create_job(job)

        scheduler_two = "test_scheduler_two"
        for i in range(5):
            job = models.Job(
                scheduler_id=scheduler_two,
                hash=f"test_hash_{i}",
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

    def get_job_by_id(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        job = models.Job(
            scheduler_id=scheduler_id,
            hash="test_hash",
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        # Act
        job = self.mock_ctx.datastores.job_store.get_job_by_id(job_db.id)

        # Assert
        self.assertEqual(job_db.id, job.id)
        self.assertEqual(job_db.scheduler_id, job.scheduler_id)
        self.assertEqual(job_db.hash, job.hash)
        self.assertEqual(job_db.p_item, job.p_item)

    def get_job_by_hash(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        job = models.Job(
            scheduler_id=scheduler_id,
            hash="test_hash",
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        job_db = self.mock_ctx.datastores.job_store.create_job(job)

        # Act
        job = self.mock_ctx.datastores.job_store.get_job_by_hash(job_db.hash)

        # Assert
        self.assertEqual(job_db.id, job.id)
        self.assertEqual(job_db.scheduler_id, job.scheduler_id)
        self.assertEqual(job_db.hash, job.hash)
        self.assertEqual(job_db.p_item, job.p_item)

    def test_update_job(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        job = models.Job(
            scheduler_id=scheduler_id,
            hash="test_hash",
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

    def update_job_enabled(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        job = models.Job(
            scheduler_id=scheduler_id,
            hash="test_hash",
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
