import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from scheduler import config, connectors, models, schedulers, storage
from structlog.testing import capture_logs

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
        self.dbconn.connect()
        models.Base.metadata.drop_all(self.dbconn.engine)
        models.Base.metadata.create_all(self.dbconn.engine)

        self.mock_ctx.datastores = SimpleNamespace(
            **{
                storage.ScheduleStore.name: storage.ScheduleStore(self.dbconn),
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

        self.mock_get_plugin = mock.patch(
            "scheduler.context.AppContext.services.katalogus.get_plugin_by_id_and_org_id",
        ).start()

        self.mock_get_object = mock.patch("scheduler.context.AppContext.services.octopoes.get_object").start()

    def tearDown(self):
        mock.patch.stopall()

    def test_is_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Act
        allowed_to_run = self.scheduler.has_boefje_permission_to_run(
            plugin,
            ooi,
        )

        # Assert
        self.assertTrue(allowed_to_run)

    def test_is_allowed_to_run_no_ooi(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Act
        allowed_to_run = self.scheduler.has_boefje_permission_to_run(
            plugin,
            ooi,
        )

        # Assert
        self.assertTrue(allowed_to_run)

    def test_is_not_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=4, consumes=[ooi.object_type])

        # Act
        with capture_logs() as cm:
            allowed_to_run = self.scheduler.has_boefje_permission_to_run(
                plugin,
                ooi,
            )

        # Assert
        self.assertFalse(allowed_to_run)
        self.assertIn("is too intense", cm[-1].get("event"))

    def test_is_task_not_running(self):
        """When both the task cannot be found in the datastore and bytes
        the task is not running.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = None
        self.mock_get_last_run_boefje.return_value = None

        # Act
        is_running = self.scheduler.has_boefje_task_started_running(boefje_task)

        # Assert
        self.assertFalse(is_running)

    def test_has_boefje_task_started_running_datastore_running(self):
        """When the task is found in the datastore and the status isn't
        failed or completed, then the task is still running.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task = functions.create_task(
            scheduler_id=self.scheduler.scheduler_id,
            data=boefje_task,
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task
        self.mock_get_last_run_boefje.return_value = None

        # Act
        is_running = self.scheduler.has_boefje_task_started_running(task)

        # Assert
        self.assertTrue(is_running)

    def test_has_boefje_task_started_running_datastore_not_running(self):
        """When the task is found in the datastore and the status is
        failed or completed, then the task is not running.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task_db_first = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            status=models.TaskStatus.COMPLETED,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        task_db_second = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
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
        is_running = self.scheduler.has_boefje_task_started_running(boefje_task)
        self.assertFalse(is_running)

        # Second run
        is_running = self.scheduler.has_boefje_task_started_running(boefje_task)
        self.assertFalse(is_running)

    def test_has_boefje_task_started_running_datastore_exception(self):
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
            self.scheduler.has_boefje_task_started_running(task)

    def test_has_boefje_task_started_running_bytes_running(self):
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
        is_running = self.scheduler.has_boefje_task_started_running(task)

        # Assert
        self.assertTrue(is_running)

    def test_has_boefje_task_started_running_bytes_not_running(self):
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
        is_running = self.scheduler.has_boefje_task_started_running(task)

        # Assert
        self.assertFalse(is_running)

    def test_has_boefje_task_started_running_bytes_exception(self):
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
            self.scheduler.has_boefje_task_started_running(task)

    def test_has_boefje_task_started_running_stalled_before_grace_period(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje_task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task_db = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            status=models.TaskStatus.DISPATCHED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        self.assertFalse(self.scheduler.has_boefje_task_stalled(boefje_task))

    def test_has_boefje_task_started_running_stalled_after_grace_period(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje_task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task_db = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            status=models.TaskStatus.DISPATCHED,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_grace_period),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        self.assertTrue(self.scheduler.has_boefje_task_stalled(boefje_task))

    def test_has_boefje_task_started_running_mismatch_before_grace_period(self):
        """When a task has finished according to the datastore, (e.g. failed
        or completed), but there are no results in bytes, we have a problem.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje_task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task_db = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            status=models.TaskStatus.COMPLETED,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        with self.assertRaises(RuntimeError):
            self.scheduler.has_boefje_task_started_running(boefje_task)

    def test_has_boefje_task_started_running_mismatch_after_grace_period(self):
        """When a task has finished according to the datastore, (e.g. failed
        or completed), but there are no results in bytes, we have a problem.
        However when the grace period has been reached we should not raise
        an error.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje_task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task_db = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            status=models.TaskStatus.COMPLETED,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_grace_period),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        self.assertFalse(self.scheduler.has_boefje_task_started_running(boefje_task))

    def test_has_boefje_task_grace_period_passed_datastore_passed(self):
        """Grace period passed according to datastore, and the status is completed"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje_task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task_db = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            status=models.TaskStatus.COMPLETED,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_grace_period),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        has_passed = self.scheduler.has_boefje_task_grace_period_passed(boefje_task)

        # Assert
        self.assertTrue(has_passed)

    def test_has_boefje_task_grace_period_passed_datastore_not_passed(self):
        """Grace period not passed according to datastore."""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje_task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task_db = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            status=models.TaskStatus.COMPLETED,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Mock
        self.mock_get_latest_task_by_hash.return_value = task_db
        self.mock_get_last_run_boefje.return_value = None

        # Act
        has_passed = self.scheduler.has_boefje_task_grace_period_passed(boefje_task)

        # Assert
        self.assertFalse(has_passed)

    def test_has_boefje_task_grace_period_passed_bytes_passed(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task_db = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            status=models.TaskStatus.COMPLETED,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
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
        has_passed = self.scheduler.has_boefje_task_grace_period_passed(boefje_task)

        # Assert
        self.assertTrue(has_passed)

    def test_has_boefje_task_grace_period_passed_bytes_not_passed(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task_db = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            status=models.TaskStatus.COMPLETED,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
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
        has_passed = self.scheduler.has_boefje_task_grace_period_passed(boefje_task)

        # Assert
        self.assertFalse(has_passed)

    def test_push_task(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(boefje.dict()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        # Mocks
        self.mock_get_latest_task_by_hash.return_value = None
        self.mock_get_last_run_boefje.return_value = None

        # Act
        self.scheduler.push_boefje_task(boefje_task)

        # Assert
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_task_no_ooi(self):
        # Arrange
        boefje = BoefjeFactory()

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(boefje.dict()),
            input_ooi=None,
            organization=self.organisation.id,
        )

        # Mocks
        self.mock_get_latest_task_by_hash.return_value = None
        self.mock_get_last_run_boefje.return_value = None

        # Act
        self.scheduler.push_boefje_task(boefje_task)

        # Assert
        self.assertEqual(1, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_boefje_task_started_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_boefje_permission_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_boefje_task_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_item_on_queue_by_hash")
    @mock.patch("scheduler.context.AppContext.datastores.task_store.get_tasks_by_hash")
    def test_push_task_queue_full(
        self,
        mock_get_tasks_by_hash,
        mock_is_item_on_queue_by_hash,
        mock_has_boefje_task_grace_period_passed,
        mock_has_boefje_permission_to_run,
        mock_has_boefje_task_started_running,
    ):
        """When the task queue is full, the task should not be pushed"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(plugin.dict()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        self.scheduler.queue.maxsize = 1
        self.scheduler.max_tries = 1

        # Mocks
        mock_has_boefje_permission_to_run.return_value = True
        mock_has_boefje_task_started_running.return_value = False
        mock_has_boefje_task_grace_period_passed.return_value = True
        mock_is_item_on_queue_by_hash.return_value = False
        mock_get_tasks_by_hash.return_value = None

        # Act
        self.scheduler.push_boefje_task(boefje_task)

        # Assert
        self.assertEqual(1, self.scheduler.queue.qsize())

        with capture_logs() as cm:
            self.scheduler.push_boefje_task(boefje_task)

        self.assertIn("Could not add task to queue, queue was full", cm[-1].get("event"))
        self.assertEqual(1, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_boefje_task_stalled")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_boefje_task_started_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_boefje_permission_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_boefje_task_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_item_on_queue_by_hash")
    @mock.patch("scheduler.context.AppContext.datastores.task_store.get_tasks_by_hash")
    def test_push_task_stalled(
        self,
        mock_get_tasks_by_hash,
        mock_is_item_on_queue_by_hash,
        mock_has_boefje_task_grace_period_passed,
        mock_has_boefje_permission_to_run,
        mock_has_boefje_task_started_running,
        mock_has_boefje_task_stalled,
    ):
        """When a task has stalled it should be set to failed."""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()

        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        item = functions.create_item(
            scheduler_id=self.organisation.id,
            priority=1,
            task=task,
        )

        # Act
        self.scheduler.push_item_to_queue(item)

        # Assert: task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje_task.boefje.id, task_pq.boefje.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(item.id)
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Act
        self.scheduler.pop_item_from_queue()

        # Assert: task should be in datastore, and dispatched
        task_db = self.mock_ctx.datastores.task_store.get_task(item.id)
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.DISPATCHED)

        # Mocks
        mock_has_boefje_permission_to_run.return_value = True
        mock_has_boefje_task_grace_period_passed.return_value = True
        mock_has_boefje_task_stalled.return_value = True
        mock_has_boefje_task_started_running.return_value = False
        self.mock_get_latest_task_by_hash.return_value = task_db
        mock_is_item_on_queue_by_hash.return_value = False
        mock_get_tasks_by_hash.return_value = None

        # Act
        self.scheduler.push_boefje_task(boefje_task)

        # Assert: task should be in datastore, and failed
        task_db = self.mock_ctx.datastores.task_store.get_task(item.id)
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.FAILED)

        # Assert: new task should be queued
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje_task.boefje.id, task_pq.boefje.id)

    def test_post_push(self):
        """When a task is added to the queue, it should be added to the database"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje_task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        item = functions.create_item(
            scheduler_id=self.organisation.id,
            priority=1,
            task=task,
        )

        # Act
        self.scheduler.push_item_to_queue(item)

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje_task.boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(item.id)
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_post_pop(self):
        """When a task is removed from the queue, its status should be updated"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje_task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        task = models.Task(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            type=models.BoefjeTask.type,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        item = functions.create_item(
            scheduler_id=self.organisation.id,
            priority=1,
            task=task,
        )

        # Act
        self.scheduler.push_item_to_queue(item)

        # Assert: task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje_task.boefje.id, task_pq.boefje.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(item.id)
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Act
        self.scheduler.pop_item_from_queue()

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(item.id)
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.DISPATCHED)

    def test_disable_scheduler(self):
        # Arrange: start scheduler
        self.scheduler.run()

        # Arrange: add tasks
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje_task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        task = functions.create_task(
            scheduler_id=self.scheduler.scheduler_id,
            data=boefje_task,
        )

        item = functions.create_item(
            scheduler_id=self.organisation.id,
            priority=1,
            task=task,
        )
        self.scheduler.push_item_to_queue(item)

        # Assert: task should be on priority queue
        pq_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_item.id, item.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(item.id)
        self.assertEqual(task_db.id, item.id)
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

    def test_has_boefje_permission_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Act
        is_allowed = self.scheduler.has_boefje_permission_to_run(plugin, ooi)

        # Assert
        self.assertTrue(is_allowed)

    def test_has_boefje_permission_to_run_boefje_disabled(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type], enabled=False)

        # Act
        is_allowed = self.scheduler.has_boefje_permission_to_run(plugin, ooi)

        # Assert
        self.assertFalse(is_allowed)

    def test_has_boefje_permission_to_run_scan_profile_is_none(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        ooi.scan_profile = None

        # Act
        is_allowed = self.scheduler.has_boefje_permission_to_run(plugin, ooi)

        # Assert
        self.assertFalse(is_allowed)

    def test_has_boefje_permission_to_run_ooi_scan_level_is_none(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        ooi.scan_profile.level = None

        # Act
        is_allowed = self.scheduler.has_boefje_permission_to_run(plugin, ooi)

        # Assert
        self.assertFalse(is_allowed)

    def test_has_boefje_permission_to_run_boefje_scan_level_is_none(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=None, consumes=[ooi.object_type])

        # Act
        is_allowed = self.scheduler.has_boefje_permission_to_run(plugin, ooi)

        # Assert
        self.assertFalse(is_allowed)


class ScanProfileMutationTestCase(BoefjeSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_has_boefje_task_started_running = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_boefje_task_started_running",
            return_value=False,
        ).start()

        self.mock_has_boefje_permission_to_run = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_boefje_permission_to_run",
            return_value=True,
        ).start()

        self.mock_has_boefje_task_grace_period_passed = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_boefje_task_grace_period_passed",
            return_value=True,
        ).start()

        self.mock_get_boefjes_for_ooi = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi",
        ).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_push_tasks_for_scan_profile_mutations(self):
        """Scan level change"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        mutation = models.ScanProfileMutation(
            operation="create", primary_key=ooi.primary_key, value=ooi
        ).model_dump_json()

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation)

        # Task should be on priority queue
        item = self.scheduler.queue.peek(0)
        task_pq = models.BoefjeTask(**item.data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(item.id)
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_scan_profile_mutations_value_empty(self):
        """When the value of a mutation is empty it should not push any tasks"""
        # Arrange
        mutation = models.ScanProfileMutation(operation="create", primary_key="123", value=None).model_dump_json()

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_scan_profile_mutations_no_boefjes_found(self):
        """When no plugins are found for boefjes, it should return no boefje tasks"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        mutation = models.ScanProfileMutation(
            operation="create", primary_key=ooi.primary_key, value=ooi
        ).model_dump_json()

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
        mutation = models.ScanProfileMutation(
            operation="create", primary_key=ooi.primary_key, value=ooi
        ).model_dump_json()

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]
        self.mock_has_boefje_permission_to_run.return_value = False

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
        mutation = models.ScanProfileMutation(
            operation="create", primary_key=ooi.primary_key, value=ooi
        ).model_dump_json()

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]
        self.mock_has_boefje_task_started_running.return_value = True

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
        mutation1 = models.ScanProfileMutation(
            operation="create", primary_key=ooi.primary_key, value=ooi
        ).model_dump_json()
        mutation2 = models.ScanProfileMutation(
            operation="create", primary_key=ooi.primary_key, value=ooi
        ).model_dump_json()

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation1)
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation2)

        # Task should be on priority queue (only one)
        task_pq = self.scheduler.queue.peek(0)
        boefje_task_pq = models.BoefjeTask(**task_pq.data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, boefje_task_pq.input_ooi)
        self.assertEqual(boefje.id, boefje_task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_scan_profile_mutations_delete(self):
        """When an OOI is deleted it should not create tasks"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        mutation1 = models.ScanProfileMutation(
            operation=models.MutationOperationType.DELETE,
            primary_key=ooi.primary_key,
            value=ooi,
        ).model_dump_json()

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation1)

        # Assert
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_scan_profile_mutations_delete_on_queue(self):
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
        ).model_dump_json()

        # Mocks
        self.mock_get_boefjes_for_ooi.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation1)

        # Assert: task should be on priority queue
        item = self.scheduler.queue.peek(0)
        task_pq = models.BoefjeTask(**item.data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Arrange
        mutation2 = models.ScanProfileMutation(
            operation=models.MutationOperationType.DELETE,
            primary_key=ooi.primary_key,
            value=ooi,
        ).model_dump_json()

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations(mutation2)

        # Assert
        self.assertIsNone(self.scheduler.queue.peek(0))
        self.assertEqual(0, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        task_db = self.mock_ctx.datastores.task_store.get_task(item.id)
        self.assertEqual(task_db.status, models.TaskStatus.CANCELLED)


class NewBoefjesTestCase(BoefjeSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_has_boefje_task_started_running = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_boefje_task_started_running",
            return_value=False,
        ).start()

        self.mock_has_boefje_permission_to_run = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_boefje_permission_to_run",
            return_value=True,
        ).start()

        self.mock_has_boefje_task_grace_period_passed = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_boefje_task_grace_period_passed",
            return_value=True,
        ).start()

        self.mock_get_new_boefjes_by_org_id = mock.patch(
            "scheduler.context.AppContext.services.katalogus.get_new_boefjes_by_org_id"
        ).start()

        self.mock_get_objects_by_object_types = mock.patch(
            "scheduler.context.AppContext.services.octopoes.get_objects_by_object_types"
        ).start()

    def tearDown(self):
        mock.patch.stopall()

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
        task_pq = self.scheduler.queue.peek(0)
        boefje_task_pq = models.BoefjeTask(**task_pq.data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, boefje_task_pq.input_ooi)
        self.assertEqual(boefje.id, boefje_task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_new_boefjes_request_exception(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        self.mock_get_objects_by_object_types.side_effect = [
            connectors.errors.ExternalServiceError("External service is not available."),
            connectors.errors.ExternalServiceError("External service is not available."),
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

    def test_push_tasks_for_new_boefjes_empty_consumes(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[])

        # Mocks
        self.mock_get_objects_by_object_types.return_value = [ooi]
        self.mock_get_new_boefjes_by_org_id.return_value = [boefje]

        # Act
        self.scheduler.push_tasks_for_new_boefjes()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_new_boefjes_empty_consumes_no_ooi(self):
        # Arrange
        boefje = PluginFactory(scan_level=0, consumes=[])

        # Mocks
        self.mock_get_objects_by_object_types.return_value = []
        self.mock_get_new_boefjes_by_org_id.return_value = [boefje]

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
            connectors.errors.ExternalServiceError("External service is not available."),
            connectors.errors.ExternalServiceError("External service is not available."),
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
        self.mock_has_boefje_permission_to_run.return_value = False

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
        self.mock_has_boefje_task_started_running.return_value = True

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
        task_pq = self.scheduler.queue.peek(0)
        boefje_task_pq = models.BoefjeTask(**task_pq.data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, boefje_task_pq.input_ooi)
        self.assertEqual(boefje.id, boefje_task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Act
        self.scheduler.push_tasks_for_new_boefjes()

        # Should only be one task on queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())


class RescheduleTestCase(BoefjeSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_has_boefje_task_started_running = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_boefje_task_started_running",
            return_value=False,
        ).start()

        self.mock_has_boefje_task_grace_period_passed = mock.patch(
            "scheduler.schedulers.BoefjeScheduler.has_boefje_task_grace_period_passed",
            return_value=True,
        ).start()

        self.mock_get_schedules = mock.patch(
            "scheduler.context.AppContext.datastores.schedule_store.get_schedules",
        ).start()

        self.mock_get_object = mock.patch(
            "scheduler.context.AppContext.services.octopoes.get_object",
        ).start()

        self.mock_get_plugin = mock.patch(
            "scheduler.context.AppContext.services.katalogus.get_plugin_by_id_and_org_id",
        ).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_push_tasks_for_rescheduling_scheduler_id(self):
        pass

    def test_push_tasks_for_rescheduling(self):
        """When the deadline of schedules have passed, the resulting task should be added to the queue"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(plugin.model_dump()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        schedule = models.Schedule(
            scheduler_id=self.scheduler.scheduler_id,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
        )

        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Mocks
        self.mock_get_schedules.return_value = ([schedule_db], 1)
        self.mock_get_object.return_value = ooi
        self.mock_get_plugin.return_value = plugin

        # Act
        self.scheduler.push_tasks_for_rescheduling()

        # Assert: new item should be on queue
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Assert: new item is created with a similar task
        peek = self.scheduler.queue.peek(0)
        self.assertEqual(schedule.hash, peek.hash)

        # Assert: task should be created, and should be the one that is queued
        task_db = self.mock_ctx.datastores.task_store.get_task(peek.id)
        self.assertIsNotNone(task_db)
        self.assertEqual(peek.id, task_db.id)

    def test_push_tasks_for_rescheduling_no_ooi(self):
        """When the deadline has passed, and when the resulting tasks doesn't
        have an OOI, it should create a task.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(plugin.model_dump()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        schedule = models.Schedule(
            scheduler_id=self.scheduler.scheduler_id,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
        )

        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Mocks
        self.mock_get_schedules.return_value = ([schedule_db], 1)
        self.mock_get_object.return_value = ooi
        self.mock_get_plugin.return_value = plugin

        # Act
        self.scheduler.push_tasks_for_rescheduling()

        # Assert: new item should be on queue
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Assert: new item is created with a similar task
        peek = self.scheduler.queue.peek(0)
        self.assertEqual(schedule_db.hash, peek.hash)

        # Assert: task should be created, and should be the one that is queued
        task_db = self.mock_ctx.datastores.task_store.get_task(peek.id)
        self.assertIsNotNone(task_db)
        self.assertEqual(peek.id, task_db.id)

    def test_push_tasks_for_rescheduling_ooi_not_found(self):
        """When ooi isn't found anymore for the schedule, we disable the schedule"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(plugin.model_dump()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        schedule = models.Schedule(
            scheduler_id=self.scheduler.scheduler_id,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
        )

        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Mocks
        self.mock_get_schedules.return_value = ([schedule_db], 1)
        self.mock_get_object.return_value = None
        self.mock_get_plugin.return_value = plugin

        # Act
        self.scheduler.push_tasks_for_rescheduling()

        # Assert: item should not be on queue
        self.assertEqual(0, self.scheduler.queue.qsize())

        # Assert: schedule should be disabled
        schedule_db_disabled = self.mock_ctx.datastores.schedule_store.get_schedule(schedule.id)
        self.assertFalse(schedule_db_disabled.enabled)

    def test_push_tasks_for_rescheduling_boefje_not_found(self):
        """When boefje isn't found anymore for the schedule, we disable the schedule"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(plugin.model_dump()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        schedule = models.Schedule(
            scheduler_id=self.scheduler.scheduler_id,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
        )

        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Mocks
        self.mock_get_schedules.return_value = ([schedule_db], 1)
        self.mock_get_object.return_value = ooi
        self.mock_get_plugin.return_value = None

        # Act
        self.scheduler.push_tasks_for_rescheduling()

        # Assert: item should not be on queue
        self.assertEqual(0, self.scheduler.queue.qsize())

        # Assert: schedule should be disabled
        schedule_db_disabled = self.mock_ctx.datastores.schedule_store.get_schedule(schedule.id)
        self.assertFalse(schedule_db_disabled.enabled)

    def test_push_tasks_for_rescheduling_boefje_disabled(self):
        """When boefje disabled for the schedule, we disable the schedule"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[ooi.object_type], enabled=False)

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(plugin.model_dump()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        schedule = models.Schedule(
            scheduler_id=self.scheduler.scheduler_id,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
        )

        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Mocks
        self.mock_get_schedules.return_value = ([schedule_db], 1)
        self.mock_get_object.return_value = ooi
        self.mock_get_plugin.return_value = plugin

        # Act
        self.scheduler.push_tasks_for_rescheduling()

        # Assert: item should not be on queue
        self.assertEqual(0, self.scheduler.queue.qsize())

        # Assert: schedule should be disabled
        schedule_db_disabled = self.mock_ctx.datastores.schedule_store.get_schedule(schedule.id)
        self.assertFalse(schedule_db_disabled.enabled)

    def test_push_tasks_for_rescheduling_boefje_doesnt_consume_ooi(self):
        """When boefje doesn't consume the ooi, we disable the schedule"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=0, consumes=[])

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(plugin.model_dump()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        schedule = models.Schedule(
            scheduler_id=self.scheduler.scheduler_id,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
        )

        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Mocks
        self.mock_get_schedules.return_value = ([schedule_db], 1)
        self.mock_get_object.return_value = ooi
        self.mock_get_plugin.return_value = plugin

        # Act
        self.scheduler.push_tasks_for_rescheduling()

        # Assert: item should not be on queue
        self.assertEqual(0, self.scheduler.queue.qsize())

        # Assert: schedule should be disabled
        schedule_db_disabled = self.mock_ctx.datastores.schedule_store.get_schedule(schedule.id)
        self.assertFalse(schedule_db_disabled.enabled)

    def test_push_tasks_for_rescheduling_boefje_cannot_scan_ooi(self):
        """When boefje cannot scan the ooi, we disable the schedule"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        plugin = PluginFactory(scan_level=1, consumes=[ooi.object_type])

        boefje_task = models.BoefjeTask(
            boefje=models.Boefje.model_validate(plugin.model_dump()),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        schedule = models.Schedule(
            scheduler_id=self.scheduler.scheduler_id,
            hash=boefje_task.hash,
            data=boefje_task.model_dump(),
        )

        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Mocks
        self.mock_get_schedules.return_value = ([schedule_db], 1)
        self.mock_get_object.return_value = ooi
        self.mock_get_plugin.return_value = plugin

        # Act
        self.scheduler.push_tasks_for_rescheduling()

        # Assert: item should not be on queue
        self.assertEqual(0, self.scheduler.queue.qsize())

        # Assert: schedule should be disabled
        schedule_db_disabled = self.mock_ctx.datastores.schedule_store.get_schedule(schedule.id)
        self.assertFalse(schedule_db_disabled.enabled)
