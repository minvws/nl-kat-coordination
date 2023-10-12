import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

import requests
from scheduler import config, connectors, models, schedulers, storage

from tests.factories import (
    BoefjeFactory,
    BoefjeMetaFactory,
    OOIFactory,
    OrganisationFactory,
    PluginFactory,
    ScanProfileFactory,
)
from tests.utils import functions


class BoefjeSchedulerBaseTestCase(unittest.TestCase):
    def setUp(self):
        # Application Context
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = config.settings.Settings()

        # Mock connectors: octopoes
        self.mock_octopoes = mock.create_autospec(
            spec=connectors.services.Octopoes,
            spec_set=True,
        )
        self.mock_ctx.services.octopoes = self.mock_octopoes

        # Mock connectors: Scan profile mutation
        self.mock_scan_profile_mutation = mock.create_autospec(
            spec=connectors.listeners.ScanProfileMutation,
            spec_set=True,
        )
        self.mock_ctx.services.scan_profile_mutation = self.mock_scan_profile_mutation

        # Mock connectors: Katalogus
        self.mock_katalogus = mock.create_autospec(
            spec=connectors.services.Katalogus,
            spec_set=True,
        )
        self.mock_ctx.services.katalogus = self.mock_katalogus

        # Mock connectors: Bytes
        self.mock_bytes = mock.create_autospec(
            spec=connectors.services.Bytes,
            spec_set=True,
        )
        self.mock_ctx.services.bytes = self.mock_bytes

        # Database
        self.dbconn = storage.DBConn(str(self.mock_ctx.config.db_uri))
        models.Base.metadata.create_all(self.dbconn.engine)
        self.mock_ctx.datastores = SimpleNamespace(
            **{
                storage.TaskStore.name: storage.TaskStore(self.dbconn),
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(self.dbconn),
            }
        )

        # Scheduler
        self.organisation = OrganisationFactory()
        self.scheduler = schedulers.BoefjeScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            organisation=self.organisation,
        )

    def tearDown(self):
        self.scheduler.stop()
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()


class BoefjeSchedulerTestCase(BoefjeSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_get_latest_task_by_hash = mock.patch(
            "scheduler.context.AppContext.datastores.task_store.get_latest_task_by_hash"
        ).start()

        self.mock_get_last_run_boefje = mock.patch(
            "scheduler.context.AppContext.services.bytes.get_last_run_boefje"
        ).start()

    def test_is_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Act
        allowed_to_run = self.scheduler.is_task_allowed_to_run(ooi=ooi, boefje=boefje)

        # Assert
        self.assertTrue(allowed_to_run)

    def test_is_not_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=4, consumes=[ooi.object_type])

        # Act
        with self.assertLogs("scheduler.schedulers", level="DEBUG") as cm:
            allowed_to_run = self.scheduler.is_task_allowed_to_run(ooi=ooi, boefje=boefje)

        # Assert
        self.assertFalse(allowed_to_run)
        self.assertIn("is too intense", cm.output[-1])

    def test_is_task_not_running(self):
        """When both the task cannot be found in the datastore and bytes
        the task is not running.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = None
        self.mock_get_last_run_boefje.return_value = None

        # Act
        is_running = self.scheduler.is_task_running(task)

        # Assert
        self.assertFalse(is_running)

    def test_is_task_running_datastore_running(self):
        """When the task is found in the datastore and the status isn't
        failed or completed, then the task is still running.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.QUEUED,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        is_running = self.scheduler.is_task_running(task)

        # Assert
        self.assertTrue(is_running)

    def test_is_task_running_datastore_not_running(self):
        """When the task is found in the datastore and the status is
        failed or completed, then the task is not running.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db_first = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        task_db_second = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.FAILED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=datetime.utcnow(),
        )

        # Mock
        self.mock_get_latest_task_by_hash.side_effect = [
            task_db_first,
            task_db_second,
        ]
        self.mock_get_last_run_boefje.return_value = last_run_boefje

        # First run
        is_running = self.scheduler.is_task_running(task)
        self.assertFalse(is_running)

        # Second run
        is_running = self.scheduler.is_task_running(task)
        self.assertFalse(is_running)

    def test_is_task_running_datastore_exception(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        # Mock
        self.mock_get_latest_task_by_hash.side_effect = Exception("Something went wrong")
        self.mock_get_last_run_boefje.return_value = None

        # Act
        with self.assertRaises(Exception):
            self.scheduler.is_task_running(task)

    def test_is_task_running_bytes_running(self):
        """When task is found in bytes and the started_at field is not None, and
        the ended_at field is None. The task is still running."""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=None,
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = None
        self.mock_get_last_run_boefje.return_value = last_run_boefje

        # Act
        is_running = self.scheduler.is_task_running(task)

        # Assert
        self.assertTrue(is_running)

    def test_is_task_running_bytes_not_running(self):
        """When task is found in bytes and the started_at field is not None, and
        the ended_at field is not None. The task is not running."""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=datetime.utcnow(),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = None
        self.mock_get_last_run_boefje.return_value = last_run_boefje

        # Act
        is_running = self.scheduler.is_task_running(task)

        # Assert
        self.assertFalse(is_running)

    def test_is_task_running_bytes_exception(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = None
        self.mock_get_last_run_boefje.return_value = Exception("Something went wrong")

        # Act
        with self.assertRaises(Exception):
            self.scheduler.is_task_running(task)

    def test_is_task_running_stalled_before_grace_period(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.DISPATCHED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        self.assertFalse(self.scheduler.is_task_stalled(task))

    def test_is_task_running_stalled_after_grace_period(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.DISPATCHED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_grace_period),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        self.assertTrue(self.scheduler.is_task_stalled(task))

    def test_is_task_running_mismatch_before_grace_period(self):
        """When a task has finished according to the datastore, (e.g. failed
        or completed), but there are no results in bytes, we have a problem.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        with self.assertRaises(RuntimeError):
            self.scheduler.is_task_running(task)

    def test_is_task_running_mismatch_after_grace_period(self):
        """When a task has finished according to the datastore, (e.g. failed
        or completed), but there are no results in bytes, we have a problem.
        However when the grace period has been reached we should not raise
        an error.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_grace_period),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        self.assertFalse(self.scheduler.is_task_running(task))

    def test_has_grace_period_passed_datastore_passed(self):
        """Grace period passed according to datastore, and the status is completed"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_grace_period),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        has_passed = self.scheduler.has_grace_period_passed(task)

        # Assert
        self.assertTrue(has_passed)

    def test_has_grace_period_passed_datastore_not_passed(self):
        """Grace period not passed according to datastore."""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        has_passed = self.scheduler.has_grace_period_passed(task)

        # Assert
        self.assertFalse(has_passed)

    def test_has_grace_period_passed_bytes_passed(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_grace_period),
        )

        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_grace_period),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = last_run_boefje

        # Act
        has_passed = self.scheduler.has_grace_period_passed(task)

        # Assert
        self.assertTrue(has_passed)

    def test_has_grace_period_passed_bytes_not_passed(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_grace_period),
        )

        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=datetime.now(timezone.utc),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = last_run_boefje

        # Act
        has_passed = self.scheduler.has_grace_period_passed(task)

        # Assert
        self.assertFalse(has_passed)

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_item_on_queue_by_hash")
    @mock.patch("scheduler.context.AppContext.datastores.task_store.get_tasks_by_hash")
    def test_push_task_queue_full(
        self,
        mock_get_tasks_by_hash,
        mock_is_item_on_queue_by_hash,
        mock_has_grace_period_passed,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
        """When the task queue is full, the task should not be pushed"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        self.scheduler.queue.maxsize = 1
        self.scheduler.max_tries = 1

        # Mocks
        mock_is_task_allowed_to_run.return_value = True
        mock_is_task_running.return_value = False
        mock_has_grace_period_passed.return_value = True
        mock_is_item_on_queue_by_hash.return_value = False
        mock_get_tasks_by_hash.return_value = None

        # Act
        self.scheduler.push_task(boefje, ooi)

        # Assert
        self.assertEqual(1, self.scheduler.queue.qsize())

        with self.assertLogs("scheduler.schedulers", level="DEBUG") as cm:
            self.scheduler.push_task(boefje, ooi)

        self.assertIn("Could not add task to queue, queue was full", cm.output[-1])
        self.assertEqual(1, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_stalled")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_item_on_queue_by_hash")
    @mock.patch("scheduler.context.AppContext.datastores.task_store.get_tasks_by_hash")
    def test_push_task_stalled(
        self,
        mock_get_tasks_by_hash,
        mock_is_item_on_queue_by_hash,
        mock_has_grace_period_passed,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
        mock_is_task_stalled,
    ):
        """When a task has stalled it should be set to failed."""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()

        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        p_item = functions.create_p_item(
            scheduler_id=self.organisation.id,
            priority=1,
            data=task,
        )

        # Act
        self.scheduler.push_item_to_queue(p_item)

        # Assert: task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(task.boefje.id, task_pq.boefje.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Act
        self.scheduler.pop_item_from_queue()

        # Assert: task should be in datastore, and dispatched
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.DISPATCHED)

        # Mocks
        mock_is_task_allowed_to_run.return_value = True
        mock_has_grace_period_passed.return_value = True
        mock_is_task_stalled.return_value = True
        mock_is_task_running.return_value = False
        self.mock_get_latest_task_by_hash.return_value = task_db
        mock_is_item_on_queue_by_hash.return_value = False
        mock_get_tasks_by_hash.return_value = None

        # Act
        self.scheduler.push_task(boefje, ooi)

        # Assert: task should be in datastore, and failed
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.FAILED)

        # Assert: new task should be queued
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_post_push(self):
        """When a task is added to the queue, it should be added to the database"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        p_item = functions.create_p_item(
            scheduler_id=self.organisation.id,
            priority=1,
            data=task,
        )

        # Act
        self.scheduler.push_item_to_queue(p_item)

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(task.boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_post_pop(self):
        """When a task is removed from the queue, its status should be updated"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        p_item = functions.create_p_item(
            scheduler_id=self.organisation.id,
            priority=1,
            data=task,
        )

        # Act
        self.scheduler.push_item_to_queue(p_item)

        # Assert: task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(task.boefje.id, task_pq.boefje.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Act
        self.scheduler.pop_item_from_queue()

        # Assert: task should be in datastore, and dispatched
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.DISPATCHED)

    def test_disable_scheduler(self):
        # Arrange: start scheduler
        self.scheduler.run()

        # Arrange: add tasks
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        p_item = functions.create_p_item(
            scheduler_id=self.organisation.id,
            priority=1,
            data=task,
        )
        self.scheduler.push_item_to_queue(p_item)

        # Assert: task should be on priority queue
        pq_p_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_p_item.id, p_item.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Assert: listeners should be running
        self.assertGreater(len(self.scheduler.listeners), 0)

        # Assert: threads should be running
        self.assertGreater(len(self.scheduler.threads), 0)

        # Act
        self.scheduler.disable()

        # Listeners should be stopped
        self.assertEqual(0, len(self.scheduler.listeners))

        # Threads should be stopped
        self.assertEqual(0, len(self.scheduler.threads))

        # Queue should be empty
        self.assertEqual(0, self.scheduler.queue.qsize())

        # All tasks on queue should be set to CANCELLED
        tasks, _ = self.mock_ctx.datastores.task_store.get_tasks(self.scheduler.scheduler_id)
        for task in tasks:
            self.assertEqual(task.status, models.TaskStatus.CANCELLED)

        # Scheduler should be disabled
        self.assertFalse(self.scheduler.is_enabled())

        self.scheduler.stop()

    def test_enable_scheduler(self):
        self.scheduler.run()

        # Assert: listeners should be running
        self.assertGreater(len(self.scheduler.listeners), 0)

        # Assert: threads should be running
        self.assertGreater(len(self.scheduler.threads), 0)

        # Disable scheduler first
        self.scheduler.disable()

        # Listeners should be stopped
        self.assertEqual(0, len(self.scheduler.listeners))

        # Threads should be stopped
        self.assertEqual(0, len(self.scheduler.threads))

        # Queue should be empty
        self.assertEqual(0, self.scheduler.queue.qsize())

        # Re-enable scheduler
        self.scheduler.enable()

        # Threads should be started
        self.assertGreater(len(self.scheduler.threads), 0)

        # Scheduler should be enabled
        self.assertTrue(self.scheduler.is_enabled())

        # Stop the scheduler
        self.scheduler.stop()

    def test_is_task_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Act
        is_allowed = self.scheduler.is_task_allowed_to_run(boefje, ooi)

        # Assert
        self.assertTrue(is_allowed)

    def test_is_task_allowed_to_run_boefje_disabled(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type], enabled=False)

        # Act
        is_allowed = self.scheduler.is_task_allowed_to_run(boefje, ooi)

        # Assert
        self.assertFalse(is_allowed)

    def test_is_task_allowed_to_run_scan_profile_is_none(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        ooi.scan_profile = None

        # Act
        is_allowed = self.scheduler.is_task_allowed_to_run(boefje, ooi)

        # Assert
        self.assertFalse(is_allowed)

    def test_is_task_allowed_to_run_ooi_scan_level_is_none(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        ooi.scan_profile.level = None

        # Act
        is_allowed = self.scheduler.is_task_allowed_to_run(boefje, ooi)

        # Assert
        self.assertFalse(is_allowed)

    def test_is_task_allowed_to_run_boefje_scan_level_is_none(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=None, consumes=[ooi.object_type])

        # Act
        is_allowed = self.scheduler.is_task_allowed_to_run(boefje, ooi)

        # Assert
        self.assertFalse(is_allowed)


class ScanProfileTestCase(BoefjeSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_is_task_running = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.is_task_running",
            return_value=False,
        ).start()

        self.mock_is_task_allowed_to_run = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run",
            return_value=True,
        ).start()

        self.mock_has_grace_period_passed = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_grace_period_passed",
            return_value=True,
        ).start()

        self.mock_get_boefjes_for_ooi = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi",
        ).start()

    def test_push_tasks_for_scan_profile_mutations(self):
        """Scan level change"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        mutation = models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi)

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation)

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_scan_profile_mutations_value_empty(self):
        """When the value of a mutation is empty it should not push any tasks"""
        # Arrange
        mutation = models.ScanProfileMutation(operation="create", primary_key="123", value=None)

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_scan_profile_mutations_no_boefjes_found(self):
        """When no plugins are found for boefjes, it should return no boefje tasks"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        mutation = models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi)

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = []

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_scan_profile_mutations_not_allowed_to_run(self):
        """When a boefje is not allowed to run, it should not be added to the queue"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        mutation = models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi)

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]
        self.mock_is_task_allowed_to_run.return_value = False

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_scan_profile_mutations_still_running(self):
        """When a boefje is still running, it should not be added to the queue"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        mutation = models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi)

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]
        self.mock_is_task_running.return_value = True

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_scan_profile_mutations_item_on_queue(self):
        """When a boefje is already on the queue, it should not be added to the queue"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        mutation1 = models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi)
        mutation2 = models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi)

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation1)
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation2)

        # Task should be on priority queue (only one)
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_task_for_scan_profile_mutations_delete(self):
        """When an OOI is deleted it should not create tasks"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        mutation1 = models.ScanProfileMutation(
            operation=models.MutationOperationType.DELETE,
            primary_key=ooi.primary_key,
            value=ooi,
        )

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation1)

        # Assert
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_task_for_scan_profile_mutations_delete_on_queue(self):
        """When an OOI is deleted, and tasks associated with that ooi
        should be removed from the queue
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        mutation1 = models.ScanProfileMutation(
            operation=models.MutationOperationType.CREATE,
            primary_key=ooi.primary_key,
            value=ooi,
        )

        mutation2 = models.ScanProfileMutation(
            operation=models.MutationOperationType.CREATE,
            primary_key=ooi.primary_key,
            value=ooi,
        )

        models.ScanProfileMutation(
            operation=models.MutationOperationType.CREATE,
            primary_key=ooi.primary_key,
            value=ooi,
        )

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation1)

        # Assert
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Arrange
        ooi.scan_profile.level = 1
        mutation2 = models.ScanProfileMutation(
            operation=models.MutationOperationType.DELETE,
            primary_key=ooi.primary_key,
            value=ooi,
        )

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation2)

        # Assert
        self.assertIsNone(self.scheduler.queue.peek(0))
        self.assertEqual(0, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.CANCELLED)


class NewBoefjesTestCase(BoefjeSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_is_task_running = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.is_task_running",
            return_value=False,
        ).start()

        self.mock_is_task_allowed_to_run = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run",
            return_value=True,
        ).start()

        self.mock_has_grace_period_passed = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_grace_period_passed",
            return_value=True,
        ).start()

        self.mock_get_new_boefjes_by_org_id = mock.patch(
            "scheduler.context.AppContext.services.katalogus.get_new_boefjes_by_org_id"
        ).start()

        self.mock_get_objects_by_object_types = mock.patch(
            "scheduler.context.AppContext.services.octopoes.get_objects_by_object_types"
        ).start()

    def test_push_tasks_for_new_boefjes(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_objects_by_object_types.return_value = [ooi]
        self.mock_get_new_boefjes_by_org_id.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_new_boefjes()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_new_boefjes_request_exception(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_objects_by_object_types.side_effect = [
            requests.exceptions.RetryError(),
            requests.exceptions.ConnectionError(),
        ]
        self.mock_get_new_boefjes_by_org_id.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_new_boefjes()
        self.scheduler.push_tasks_for_new_boefjes()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_new_boefjes_no_new_boefjes(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)

        # Mocks
        self.mock_get_objects_by_object_types.return_value = [ooi]
        self.mock_get_new_boefjes_by_org_id.return_value = []

        # Act
        self.scheduler.push_tasks_for_new_boefjes()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_new_boefjes_no_oois_found(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_objects_by_object_types.return_value = []
        self.mock_get_new_boefjes_by_org_id.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_new_boefjes()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_new_boefjes_get_objects_request_exception(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_objects_by_object_types.side_effect = [
            requests.exceptions.RetryError(),
            requests.exceptions.ConnectionError(),
        ]
        self.mock_get_new_boefjes_by_org_id.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_new_boefjes()
        self.scheduler.push_tasks_for_new_boefjes()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_new_boefjes_not_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_objects_by_object_types.return_value = [ooi]
        self.mock_get_new_boefjes_by_org_id.return_value = [boefje]
        self.mock_is_task_allowed_to_run.return_value = False

        # Act
        self.scheduler.push_tasks_for_new_boefjes()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_new_boefjes_still_running(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_objects_by_object_types.return_value = [ooi]
        self.mock_get_new_boefjes_by_org_id.return_value = [boefje]
        self.mock_is_task_running.return_value = True

        # Act
        self.scheduler.push_tasks_for_new_boefjes()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_new_boefjes_item_on_queue(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_objects_by_object_types.return_value = [ooi]
        self.mock_get_new_boefjes_by_org_id.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_new_boefjes()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Act
        self.scheduler.push_tasks_for_new_boefjes()

        # Should only be one task on queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())


class RandomObjectsTestCase(BoefjeSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_is_task_running = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.is_task_running",
            return_value=False,
        ).start()

        self.mock_is_task_allowed_to_run = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run",
            return_value=True,
        ).start()

        self.mock_has_grace_period_passed = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_grace_period_passed",
            return_value=True,
        ).start()

        self.mock_get_boefjes_for_ooi = mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi").start()

        self.mock_get_random_objects = mock.patch(
            "scheduler.context.AppContext.services.octopoes.get_random_objects"
        ).start()

    def test_push_tasks_for_random_objects(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_random_objects.side_effect = [[ooi], [], [], []]
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_random_objects_queue_full(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        PluginFactory(scan_level=0, consumes=[ooi.object_type])

        self.scheduler.queue.maxsize = 1
        self.scheduler.max_tries = 1

        self.scheduler.push_tasks_for_random_objects()
        self.assertEqual(0, self.scheduler.queue.qsize())

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Assert: task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_random_objects_request_exception(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_random_objects.side_effect = [
            requests.exceptions.RetryError(),
            requests.exceptions.ConnectionError(),
        ]

        # Act
        self.scheduler.push_tasks_for_random_objects()
        self.scheduler.push_tasks_for_random_objects()

        # Assert: task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_random_objects_no_random_oois(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_random_objects.return_value = []

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Assert: task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.context.AppContext.datastores.task_store.get_tasks_by_hash")
    def test_push_tasks_for_random_objects_prior_tasks(self, mock_get_tasks_by_hash):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task.model_dump(),
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Mocks
        self.mock_get_random_objects.side_effect = [[ooi], [], [], []]
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        mock_get_tasks_by_hash.return_value = [task_db]

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_random_objects_no_boefjes_found(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)

        # Mocks
        self.mock_get_random_objects.side_effect = [[ooi], [], [], []]
        self.mock_get_boefjes_for_ooi.return_value = []

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_random_objects_not_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_random_objects.side_effect = [[ooi], [], [], []]
        self.mock_get_boefjes_for_ooi.return_value = [boefje]
        self.mock_is_task_allowed_to_run.return_value = False

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_random_objects_still_running(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_random_objects.side_effect = [[ooi], [], [], []]
        self.mock_get_boefjes_for_ooi.return_value = [boefje]
        self.mock_is_task_running.return_value = True

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_random_objects_item_on_queue(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_random_objects.side_effect = [[ooi], [], [], []]
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)
